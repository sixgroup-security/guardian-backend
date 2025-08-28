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

from __future__ import annotations

import json
import logging
from uuid import UUID
from datetime import datetime
from typing import Annotated, List, Dict
from fastapi import Body, Depends, APIRouter, Security, BackgroundTasks, Request, Response, status
from fastapi.testclient import TestClient
from fastapi.exceptions import ResponseValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from schema import get_db, VulnerabilityStatus
from schema.util import (
    ApiPermissionEnum, StatusMessage, StatusEnum, InvalidDataError, update_database_record, NotFoundError
)
from schema.project import ProjectReport, ReportGenerationInfo, ReportRequestType
from schema.reporting import ReportCreationStatus
from schema.reporting.report import ReportReport, Report
from schema.reporting.report_version import (
    ReportVersion, ReportVersionCreate, ReportVersionReport, ReportVersionUpdate, ReportVersionStatus
)
from schema.reporting.report_section_management.vulnerability import IncompleteVulnerabilityError
from routers.user import User, get_current_active_user, get_logger
from routers.project import check_access_permission, get_project
from routers.reporting.report import API_REPORT_PREFIX
from . import (
    download_pdf, download_pdf_log, download_xlsx, download_tex, download_json, return_pdf, publish_report_creation,
    deliver_report_sql
)

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_REPORT_VERSION_PREFIX = API_REPORT_PREFIX + "/{report_id}/versions"

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix=API_REPORT_VERSION_PREFIX,
    tags=["report"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def request_report_version_regeneration(path: str, cookies: Dict[str, str]):
    """
    Sends an HTTP(S) request to REST API endpoint to regenerate the report
    """
    with TestClient(router) as client:
        client.put(path, cookies=cookies)


def check_unique(version: ReportVersionCreate | ReportVersionUpdate, report: ProjectReport):
    """
    Checks if the given version already exist in the database.
    """
    version_id = version.id if isinstance(version, ReportVersionUpdate) else None
    result = [item for item in report.versions if item.version == version.version and item.id != version_id]
    if result:
        raise InvalidDataError("Could not add version because version already exist.")


def check_report_version(report: Report, version_status: ReportVersionStatus | None):
    """
    Check if the report is ready for versioning.
    """
    for section in report.sections:
        if section.hide:
            continue
        for vulnerability in section.vulnerabilities:
            if version_status and version_status == ReportVersionStatus.final and vulnerability.status in [
                VulnerabilityStatus.draft, VulnerabilityStatus.review
            ]:
                raise IncompleteVulnerabilityError(f"In order to create a report version in status Final, all vulnerabilities must be in status Final, Resolved or Hide.")
            vulnerability.check_complete()


@router.post("", response_model=StatusMessage)
async def create_report_version(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    item: Annotated[ReportVersionCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new report version.
    """
    check_access_permission(current_user, project)
    try:
        result = StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Report version successfully created."
        )
        report = project.get_report(report_id, must_exist=True)
        # Make sure the report version does not exist already
        check_unique(version=item, report=report)
        # Check if the report is ready for versioning
        check_report_version(report, item.status)
        # Create the JSON object
        project_report = ProjectReport.from_orm(project)
        project_report.report = ReportReport.from_orm(report)
        # We need to add the current version
        project_report.report.versions.append(ReportVersionReport(**item.model_dump(), created_at=datetime.now()))
        json_object = json.loads(project_report.json())
        version = ReportVersion(
            **item.model_dump(),
            creation_status=ReportCreationStatus.scheduled,
            json_object=json_object,
            report_id=report.id,
            user_id=current_user.id
        )
        session.add(version)
        session.commit()
        logger.debug("Report version committed ...")
        # Check if the report is ready for versioning
        if incomplete := project_report.get_incomplete_fields():
            result = StatusMessage(
                status=status.HTTP_200_OK,
                severity=StatusEnum.warning,
                message=f"Report generation task successfully created but the following attributes are missing: "
                        f"{', '.join(incomplete)}"
            )
        # Send the report's JSON object to the message queue for PDF, XLSX and TEX file creation.
        await publish_report_creation(
            info=ReportGenerationInfo(
                type=ReportRequestType.report,
                project=project_report,
                requestor=current_user
            ),
            item_class=ReportVersion,
            item_id=version.id,
            logger=logger,
            payload={"invalidateQueries": [["report", {"report": str(report.id)}, "overview", "version"]]},
        )
        return result
    except ValueError as ex:
        logger.exception(ex)
        return StatusMessage(
            status=status.HTTP_400_BAD_REQUEST,
            severity=StatusEnum.error,
            message=f"Report version creation failed with unknown error."
        )
    except ResponseValidationError as ex:
        logger.exception(ex)
        return StatusMessage(
            status=status.HTTP_400_BAD_REQUEST,
            severity=StatusEnum.error,
            message=f"Report version creation failed with unknown error."
        )
    except IncompleteVulnerabilityError as ex:
        logger.exception(ex)
        return StatusMessage(
            status=status.HTTP_400_BAD_REQUEST,
            severity=StatusEnum.error,
            message=str(ex)
        )
    except Exception as ex:
        raise InvalidDataError(str(ex))


@router.delete("/{version_id}", response_model=StatusMessage)
def delete_report_version(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name]
    )],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Deletes a report version by its ID.
    """
    check_access_permission(current_user, project)
    try:
        if result := project.get_item(report_id=report_id, report_version_id=version_id):
            session.delete(result)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Report version successfully deleted."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("", response_model=StatusMessage)
async def update_report_version(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name]
    )],
    request: Request,
    background_tasks: BackgroundTasks,
    logger: Annotated[logging.Logger, Depends(get_logger)],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    item: Annotated[ReportVersionUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a report version by its ID.
    """
    check_access_permission(current_user, project)
    try:
        result = StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Report version successfully updated."
        )
        # We have to ensure that the report version exists in the given report and project
        if not (report_version := project.get_item(report_id=report_id, report_version_id=item.id)):
            return StatusMessage(
                status=status.HTTP_400_BAD_REQUEST,
                severity=StatusEnum.error,
                message=f"Report version could not be updated."
            )
        # Make sure the report version does not exist already
        check_unique(version=item, report=report_version.report)
        # We update the report
        update_database_record(
            session=session,
            source=item,
            source_model=ReportVersionUpdate,
            query_model=ReportVersion,
            commit=True
        )
        # We schedule regenerating report regeneration
        background_tasks.add_task(
            request_report_version_regeneration,
            path=f"{request.url.path.rstrip('/')}/{item.id}/regenerate",
            cookies=request.cookies
        )
        return result
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e)) from e


@router.get("", response_model=List[Dict])
def read_report_versions(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    report_id: UUID,
    project: UUID = Depends(get_project),
    session: Session = Depends(get_db)
):
    """
    Returns all report versions.
    """
    check_access_permission(current_user, project)
    sql = """
    SELECT
        json_agg(
            json_build_object(
                'id', rv.id,
                'version', rv.version,
                'username', rv.username,
                'comment', rv.comment,
                'status', CASE
                        WHEN rv.status IS NULL THEN NULL
                        WHEN rv.status = 'draft' THEN 0
                        WHEN rv.status = 'final' THEN 10
                    END,
                'report_date', rv.report_date,
                'user', CHOOSE_VALUE(u.id IS NULL, NULL, json_build_object(
                    'id', u.id,
                    'email', u.email,
                    'full_name', u.full_name
                )),
                'creation_status', CASE
                        WHEN rv.creation_status IS NULL THEN NULL
                        WHEN rv.creation_status = 'scheduled' THEN 5
                        WHEN rv.creation_status = 'generating' THEN 10
                        WHEN rv.creation_status = 'successful' THEN 20
                        WHEN rv.creation_status = 'failed' THEN 30
                    END,
                'has_pdf', rv.pdf IS NOT NULL,
                'has_xlsx', rv.xlsx IS NOT NULL,
                'has_pdf_log', rv.pdf_log IS NOT NULL,
                'has_tex', rv.tex IS NOT NULL
            ) ORDER BY rv.version
        )
    FROM reportversion rv
        INNER JOIN report r ON r.id = rv.report_id
        INNER JOIN project p ON p.id = r.project_id
        LEFT JOIN "user" u ON u.id = rv.user_id
        WHERE p.id = :project_id AND rv.report_id = :report_id
    """
    result = session.execute(text(sql), {'report_id': report_id, 'project_id': project.id})
    versions = result.scalar_one_or_none()
    return versions if versions else []


@router.put("/{version_id}/regenerate", response_model=StatusMessage)
async def regenerate_report_version(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name]
    )],
    project: Annotated[UUID, Depends(get_project)],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
) -> StatusMessage:
    """
    Regenerates the report files for the given report version.
    """
    check_access_permission(current_user, project)
    try:
        result = StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Report generation task successfully scheduled."
        )
        report = project.get_item(report_id=report_id)
        if version := report.get_version(report_version_id=version_id):
            if version.creation_status not in [ReportCreationStatus.successful, ReportCreationStatus.failed]:
                return StatusMessage(
                    status=status.HTTP_200_OK,
                    severity=StatusEnum.info,
                    message=f"Report generation task is already running. Wait until it has completed or failed and "
                            f"run again."
                )
            # Obtain report version from database
            # If last report version, then we recreate the JSON object
            if version.version == report.versions[-1].version:
                # Check if the report is ready for versioning
                check_report_version(report, version.status)
                # Create the JSON object
                project_report = ProjectReport.from_orm(project)
                project_report.report = ReportReport.from_orm(report)
                # We need to add the current version
                project_report.report.versions[-1] = ReportVersionReport(**version.model_dump())
                # Update JSON object in database
                version.json_object = json.loads(project_report.json())
                # Check if the report is ready for versioning
                if incomplete := project_report.get_incomplete_fields():
                    result = StatusMessage(
                        status=status.HTTP_200_OK,
                        severity=StatusEnum.warning,
                        message=f"Report generation task successfully created but the following attributes are missing: "
                                f"{', '.join(incomplete)}"
                    )
            else:
                project_report = version.json_object
            # Update remaining attributes
            version.creation_status = ReportCreationStatus.scheduled
            version.pdf = None
            version.pdf_log = None
            version.tex = None
            version.xlsx = None
            session.commit()
            # Send the report's JSON object to the message queue for PDF, XLSX and TEX file creation.
            await publish_report_creation(
                info=ReportGenerationInfo(
                    type=ReportRequestType.report,
                    project=project_report,
                    requestor=current_user
                ),
                item_class=ReportVersion,
                item_id=version.id,
                logger=logger,
                payload={"invalidateQueries": [["report", {"report": str(report.id)}, "overview", "version"]]}
            )
        else:
            result = StatusMessage(
                status=status.HTTP_400_BAD_REQUEST,
                severity=StatusEnum.error,
                message=f"Report generation task scheduling failed."
            )
        return result
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/{version_id}/json")
def read_report_version_json(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns the entire report as JSON for the given report version.
    """
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="json_object",
        delivery_fn=download_json
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result


@router.get("/{version_id}/pdf")
def read_report_version_pdf(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns the entire report as PDF for the given report version.
    """
    # We check access permissions
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    # We obtain response object
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="pdf",
        delivery_fn=download_pdf
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result


@router.get("/{version_id}/view-pdf")
def read_report_version_view_pdf(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
) -> Response:
    """
    Returns the entire report as PDF for the given report version.
    """
    # We check access permissions
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    # We obtain response object
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="pdf",
        delivery_fn=return_pdf
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result


@router.get("/{version_id}/tex")
def read_report_version_tex(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns the tex package for entire report version.
    """
    # We check access permissions
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    # We obtain response object
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="tex",
        delivery_fn=download_tex
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result


@router.get("/{version_id}/pdf-log")
def read_report_version_log(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns the pdflatex log file.
    """
    # We check access permissions
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    # We obtain response object
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="pdf_log",
        delivery_fn=download_pdf_log
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result


@router.get("/{version_id}/xlsx")
def read_report_version_xlsx(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns the entire report as Excel file for the given report version.
    """
    # We check access permissions
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    # We obtain response object
    if not (result := deliver_report_sql(
        session=session,
        project=project,
        report_id=report_id,
        report_version_id=version_id,
        report_version_column="xlsx",
        delivery_fn=download_xlsx
    )):
        result = Response(content="File not found.", media_type="text/plain")
    return result
