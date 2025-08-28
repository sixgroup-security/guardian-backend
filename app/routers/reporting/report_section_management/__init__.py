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

import logging
from fastapi import status
from sqlalchemy.orm import Session
from routers.user import User
from routers.reporting import publish_report_creation
from schema.util import update_attributes
from schema.reporting.report_section_management.vulnerability import Vulnerability, VulnerabilityStatus
from schema.database.redis_client import RedisConnectionError
from schema.util import StatusMessage, StatusEnum
from schema.project import Project
from schema.reporting.report import Report
from schema import ReportGenerationInfo, ProjectReport, ReportReport, ReportRequestType


__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

# Lookup: Check Report Version
IN_SCOPE_STATES = [VulnerabilityStatus.review, VulnerabilityStatus.final, VulnerabilityStatus.resolved]


async def update_vulnerability_generic(
        session: Session,
        current: Vulnerability | None,
        new: Vulnerability,
        project: Project,
        report: Report,
        current_user: User,
        logger: logging.Logger
) -> StatusMessage:
    """
    Updates a vulnerability and sends the report to the message queue.
    """
    result = StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Vulnerability successfully updated."
    )
    if not current:
        return result
    try:
        # As we only create the report for vulnerabilities in status Review, Final or Resolved, we only check whether
        # these vulnerabilities are complete.
        if new.status in IN_SCOPE_STATES:
            new.check_complete(with_status=False)
        exclude = {
            "vrt_category_id",
            "owasp_top_ten_id",
            "source_template_id"
        } if current.source_template_id else None
        vulnerability = update_attributes(
            target=current,
            source=new,
            source_model=Vulnerability,
            exclude_unset=True,
            exclude=exclude
        )
        # Send the report's JSON object to the message queue for PDF and TEX file creation.
        project_report = ProjectReport.from_orm(project)
        project_report.report = ReportReport.from_orm(report)
        session.commit()
        # Lookup: Check Report Version
        # We only create vulnerabilities that we checked for their completeness.
        # if current.status in IN_SCOPE_STATES:
        #     await publish_report_creation(
        #         info=ReportGenerationInfo(
        #             type=ReportRequestType.vulnerability,
        #             project=project_report,
        #             requestor=current_user,
        #             vulnerabilities=[current.id]
        #         ),
        #         item_class=Vulnerability,
        #         item_id=vulnerability.id,
        #         logger=logger
        #     )
    except RedisConnectionError:
        return StatusMessage(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            severity=StatusEnum.error,
            message=f"Vulnerability successfully saved but PDF report generation task failed because the message "
                    f"queue is not available."
        )
    return result
