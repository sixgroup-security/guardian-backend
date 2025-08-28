# This file is part of Guardian.
#
# Guardian is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Guardian is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Guardian. If not, see <https://www.gnu.org/licenses/>.

import uuid
import json
import logging
from fastapi import Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from redis.exceptions import RedisError
from typing import Callable, Any, ClassVar, Dict
from schema import ReportGenerationInfo, SessionLocal, base_settings
from schema.user import User
from schema.project import Project
from schema.websocket import manager
from schema.util import InvalidDataError, StatusMessage, StatusEnum
from schema.reporting import ReportCreationStatus
from schema.reporting.report_version import ReportVersion, ReportVersionStatus
from schema.database.redis_client import publish as redis_publish, RedisConnectionError
from schema.reporting.report_section_management.vulnerability import Vulnerability
from routers.project import check_access_permission, get_project


__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


async def publish_report_creation(
        info: ReportGenerationInfo,
        item_class: ClassVar,
        item_id: uuid.UUID,
        logger: logging.Logger,
        payload: Dict = None
):
    """
    Generic function used to send report generation tasks to the Guardian Reporting micro service.
    """
    try:
        logger.debug("Entered background task to send report to redis ...")
        await redis_publish(
            username=base_settings.redis_user_report_write,
            password=base_settings.redis_password_report_write,
            channel=base_settings.redis_report_channel,
            message=info.json()
        )
    except RedisError as ex:
        logger.info("Publishing report to Redis failed ...")
        logger.exception(ex)
        # Update database
        try:
            with SessionLocal() as session:
                session.query(item_class).filter_by(id=item_id).update(
                    {"creation_status": ReportCreationStatus.failed.name}
                )
                session.commit()
        except Exception as e:
            logger.exception(e)
        # Notify user via WebSocket
        await manager.send(
            user=info.requestor,
            status=StatusMessage(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                severity=StatusEnum.error,
                message=f"PDF report generation task failed because the message queue is not available.",
                payload=payload
            )
        )
        raise RedisConnectionError()


def get_report_file_name(
        project: Project,
        report_version_status: ReportVersionStatus,
        report_version: float
) -> str:
    """
    Returns the file name for a report version.
    """
    return f"{project.project_id}_{report_version_status.name.capitalize()}-Report_v{report_version}"


def get_file_name(item: ReportVersion | Vulnerability):
    """
    Returns the file name for a report version.
    """
    if isinstance(item, ReportVersion):
        return get_report_file_name(
            project=item.report.project,
            report_version_status=item.status,
            report_version=item.version
        )
    elif isinstance(item, Vulnerability):
        return f"{item.report_section.report.project.project_id}_{item.vulnerability_id_str}"


def deliver_report_sql(
        session: Session,
        project: Project,
        report_id: uuid.UUID,
        report_version_id: uuid.UUID,
        report_version_column: str,
        delivery_fn: Callable[[Any, str], Response]
) -> Response | None:
    """
    Generic method that allows downloading a report file directly via a SQL statement. Resource-wise this is
    better than using SQLAlchemy.
    """
    sql = f"""
        WITH report_version AS (
            SELECT
                id,
                status,
                version,
                report_id,
                {report_version_column} as content
            FROM reportversion
                WHERE id = :version_id
        )
        SELECT
            rv.status,
            rv.version,
            rv.content
        FROM report_version rv
            INNER JOIN report r ON r.id = rv.report_id
            INNER JOIN project p ON p.id = r.project_id
            WHERE p.id = :project_id
                AND rv.report_id = :report_id
        """
    if (result := session.execute(text(sql), {
        'version_id': report_version_id,
        'report_id': report_id,
        'project_id': project.id
    }).one_or_none()):
        version_status, version, content = result.t
        file_name = get_report_file_name(
            project=project,
            report_version_status=ReportVersionStatus[version_status],
            report_version=float(version)
        )
        return delivery_fn(content, file_name)
    return None


def deliver_report_file(
        session: Session,
        user: User,
        delivery_fn: Callable[[Any, str], Response],
        project_id: uuid.UUID,
        **kwargs
):
    """
    Generic method that allows downloading a report file.
    """
    project = get_project(project_id, session=session)
    check_access_permission(user, project)
    try:
        result = project.get_item(**kwargs)
        file_name = get_file_name(result)
        return delivery_fn(result, file_name)
    except Exception as e:
        raise InvalidDataError(str(e))


def download_json(result: Dict, file_name: str) -> Response | None:
    """
    Delivery function for deliver_report_file that allows downloading a JSON file.
    """
    if result:
        file_ext = "json"
        content_type = "application/json"
        content = json.dumps(result, indent=2)
    else:
        file_ext = "txt"
        content_type = "text/plain"
        content = "File not found."
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}.{file_ext}"
        }
    )


def download_pdf(result: Any, file_name: str) -> Response | None:
    """
    Delivery function for deliver_report_file that allows downloading a PDF report.
    """
    file_ext = "pdf"
    content_type = "application/pdf"
    if not (content := result.pdf if isinstance(result, Vulnerability) else result):
        file_ext = "txt"
        content_type = "text/plain"
        content = "File not found."
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}.{file_ext}"
        }
    )


def return_pdf(result: Any, file_name: str) -> Response | None:
    """
    Delivery function for deliver_report_file that allows viewing a PDF report.
    """
    if not (content := result.pdf if isinstance(result, Vulnerability) else result):
        return None
    return Response(
        content=content,
        media_type="application/pdf"
    )


def download_pdf_log(result: Any, file_name: str):
    """
    Delivery function for deliver_report_file that allows downloading a log file about PDF creation.
    """
    file_ext = "log"
    content_type = "text/plain"
    if not (content := result.pdf_log if isinstance(result, Vulnerability) else result):
        file_ext = "txt"
        content = "File not found."
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}.{file_ext}"
        }
    )


def download_tex(result: Any, file_name: str):
    """
    Delivery function for deliver_report_file that allows downloading the LaTeX files.
    """
    file_ext = "zip"
    content_type = "application/zip"
    if not (content := result.tex if isinstance(result, Vulnerability) else result):
        file_ext = "txt"
        content = "File not found."
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}.{file_ext}"
        }
    )


def download_xlsx(result: Any, file_name: str):
    """
    Delivery function for deliver_report_file that allows downloading an Excel file.
    """
    file_ext = "xlsx"
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if not (content := result.xlsx if isinstance(result, Vulnerability) else result):
        file_ext = "txt"
        content = "File not found."
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}.{file_ext}"
        }
    )
