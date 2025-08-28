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

import logging
from uuid import UUID
from typing import Annotated, Optional, List
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import (
    ApiPermissionEnum, update_attributes, StatusMessage, StatusEnum, InvalidDataError, InternalServerError
)
from schema.reporting.vulnerability.rating import Rating, RatingLookup
from schema.reporting.vulnerability.measure import Measure, VulnerabilityMeasureLookup
from schema.reporting.report_section_management.vulnerability import (
    Vulnerability, VulnerabilityRead, VulnerabilityUpdate
)
from schema.reporting.vulnerability.vulnerability_template import VulnerabilityTemplate, VulnerabilityTemplateMeasure
from schema.reporting.report_section_management.report_section import (
    ReportSection, ReportSectionCreate, ReportSectionUpdate
)
from routers.user import get_current_active_user, User
from routers.project import check_access_permission, get_project
from routers.reporting.report import API_REPORT_PREFIX
from . import update_vulnerability_generic
from .. import deliver_report_file, download_pdf, download_pdf_log, download_tex


__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_REPORT_SECTION_PREFIX = API_REPORT_PREFIX + "/{report_id}/report-sections"

router = APIRouter(
    prefix=API_REPORT_SECTION_PREFIX,
    tags=["report"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.post("", response_model=StatusMessage)
def create_report_section(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name]
    )],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    item: Annotated[ReportSectionCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new report section.
    """
    check_access_permission(current_user, project)
    try:
        report = project.get_report(report_id, must_exist=True)
        order = (max([item.order for item in report.sections]) if report.sections else 0) + 10
        section = ReportSection(**item.model_dump(), order=order)
        report.sections.append(section)
        session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Section successfully added."
        )
    except ValueError as e:
        logger.exception(e)
        raise InternalServerError(e)
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("", response_model=StatusMessage)
def update_report_section(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name])
    ],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    item: Annotated[ReportSectionUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a report section.
    """
    check_access_permission(current_user, project)
    try:
        if result := project.get_item(report_id=report_id, report_section_id=item.id):
            updated = ReportSection(**item.model_dump())
            update_attributes(target=result, source=updated, source_model=ReportSection, exclude_unset=True)
            session.add(result)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Section successfully added."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.delete("/{section_id}", response_model=StatusMessage)
def delete_report_section(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_update.name]
    )],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Deletes a report section.
    """
    check_access_permission(current_user, project)
    try:
        if result := project.get_item(report_id=report_id, report_section_id=section_id):
            session.delete(result)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Section successfully deleted."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{section_id}/move-down", response_model=StatusMessage)
def move_report_section_up(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Changes the order of a report section.
    """
    check_access_permission(current_user, project)
    try:
        section = project.get_item(report_id=report_id, report_section_id=section_id)
        if sections := list(
                filter(lambda x: x.order > section.order, sorted(section.report.sections, key=lambda x: x.order))):
            current_order = section.order
            section.order = sections[0].order
            sections[0].order = current_order
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Order successfully updated."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{section_id}/move-up", response_model=StatusMessage)
def move_report_section_down(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Changes the order of a report section.
    """
    check_access_permission(current_user, project)
    try:
        section = project.get_item(report_id=report_id, report_section_id=section_id)
        if sections := list(
                filter(lambda x: x.order < section.order, sorted(section.report.sections, key=lambda x: x.order))):
            current_order = section.order
            section.order = sections[-1].order
            sections[-1].order = current_order
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Order successfully updated."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("", response_model=List[ReportSection])
def get_all_report_sections(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID
):
    """
    Returns all report sections for the given report.
    """
    check_access_permission(current_user, project)
    try:
        report = project.get_report(report_id)
        return report.sections if report else []
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/{section_id}/vulnerabilities", response_model=List[VulnerabilityRead])
def read_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_read.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
):
    """
    Returns all vulnerabilities in the given report section.
    """
    check_access_permission(current_user, project)
    try:
        result = project.get_item(report_id=report_id, report_section_id=section_id)
        return result.vulnerabilities if result else []
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}", response_model=Optional[VulnerabilityRead])
def read_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_read.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID
):
    """
    Returns a vulnerability in the given report section.
    """
    check_access_permission(current_user, project)
    try:
        result = project.get_item(
            report_id=report_id,
            report_section_id=section_id,
            vulnerability_id=vulnerability_id
        )
        return result if result else {}
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{section_id}/vulnerabilities/{vulnerability_id}", response_model=StatusMessage)
# /api/v1/projects/{project_id}/reports/{report_id}/report-sections/{section_id}/vulnerabilities/{vulnerability_id}
async def update_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    vulnerability: Annotated[VulnerabilityUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates the vulnerability in the given report section.
    """
    project = get_project(project_id, session)
    report = project.get_report(report_id)
    check_access_permission(current_user, project)
    try:
        new = Vulnerability(**vulnerability.model_dump(), id=vulnerability_id)
        current = project.get_item(
            report_id=report_id,
            report_section_id=section_id,
            vulnerability_id=vulnerability_id
        )
        return await update_vulnerability_generic(
            session=session,
            current=current,
            new=new,
            project=project,
            report=report,
            current_user=current_user,
            logger=logger
        )
    except ValueError as e:
        logger.exception(e)
        raise InternalServerError(e)
    except Exception as e:
        raise InvalidDataError(str(e))


@router.post("/{section_id}/vulnerabilities/new", response_model=StatusMessage)
def create_new_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Creates a new vulnerability in the given report section.
    """
    project = get_project(project_id, session)
    check_access_permission(current_user, project)
    try:
        report = project.get_report(report_id, must_exist=True)
        report_section = report.get_section(report_section_id=section_id)
        if report_section:
            result = Vulnerability.create_empty(
                title=f"New Vulnerability for {current_user.full_name}",
                report_section=report_section
            )
            report_section.vulnerabilities.append(result)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Vulnerability successfully created."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.post("/{section_id}/vulnerabilities/{vulnerability_id}", response_model=StatusMessage)
def create_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Creates a new vulnerability in the given report section.
    """
    project = get_project(project_id, session)
    check_access_permission(current_user, project)
    try:
        report = project.get_report(report_id, must_exist=True)
        report_section = report.get_section(report_section_id=section_id)
        if report_section:
            template = session.query(VulnerabilityTemplate).filter_by(id=vulnerability_id).one_or_none()
            if template:
                result = Vulnerability.clone_from_template(language=report.report_language,
                                                           template=template,
                                                           report_section=report_section)
                report_section.vulnerabilities.append(result)
                session.commit()
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Vulnerability successfully created."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.delete("/{section_id}/vulnerabilities/{vulnerability_id}", response_model=StatusMessage)
def delete_vulnerability(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Deletes a vulnerability in the given report section.
    """
    project = get_project(project_id, session)
    check_access_permission(current_user, project)
    try:
        current = project.get_item(
            report_id=report_id,
            report_section_id=section_id,
            vulnerability_id=vulnerability_id
        )
        if current:
            session.delete(current)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Vulnerability successfully deleted."
        )
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}/ratings", response_model=List[RatingLookup])
def read_vulnerability_ratings(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_read.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns a vulnerability's rating templates.
    """
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    try:
        result = []
        report = project.get_report(report_id, must_exist=True)
        vulnerability = report.get_item(
            report_section_id=section_id,
            vulnerability_id=vulnerability_id
        )
        if vulnerability and vulnerability.source_template_id:
            result = [
                RatingLookup(
                    **item.model_dump(),
                    comment=item.get_comment(report.report_language)
                ) for item in session.query(Rating).filter_by(vulnerability_id=vulnerability.source_template_id).all()
            ]
        return result
    except ValueError as ex:
        logger.exception(ex)
        raise InvalidDataError(str(ex))
    except Exception as ex:
        raise InvalidDataError(str(ex))


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}/measures",
            response_model=List[VulnerabilityMeasureLookup])
def read_vulnerability_measures(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Returns a vulnerability's measure templates.
    """
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    try:
        result = []
        report = project.get_report(report_id, must_exist=True)
        vulnerability = report.get_item(
            report_section_id=section_id,
            vulnerability_id=vulnerability_id
        )
        if vulnerability and vulnerability.source_template_id:
            result = [VulnerabilityMeasureLookup(**item.model_dump(),
                                                 recommendation=item.get_recommendation(report.report_language))
                      for item in session.query(Measure)
                      .join(VulnerabilityTemplateMeasure)
                      .filter(VulnerabilityTemplateMeasure.vulnerability_id == vulnerability.source_template_id).all()]
        return result
    except ValueError as e:
        logger.exception(e)
        raise InternalServerError(e)
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}/pdf", response_model=Optional[VulnerabilityRead])
def get_vulnerability_pdf(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Downloads the PDF file of the given vulnerability.
    """
    return deliver_report_file(
        session=session,
        user=current_user,
        project_id=project_id,
        report_id=report_id,
        report_section_id=section_id,
        vulnerability_id=vulnerability_id,
        delivery_fn=download_pdf
    )


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}/pdf-log", response_model=Optional[VulnerabilityRead])
def get_vulnerability_pdf_log(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Downloads the PDF creation log file for the given vulnerability.
    """
    return deliver_report_file(
        session=session,
        user=current_user,
        project_id=project_id,
        report_id=report_id,
        report_section_id=section_id,
        vulnerability_id=vulnerability_id,
        delivery_fn=download_pdf_log
    )


@router.get("/{section_id}/vulnerabilities/{vulnerability_id}/tex", response_model=Optional[VulnerabilityRead])
def get_vulnerability_tex(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.pentest_report_read.name]
    )],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    vulnerability_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Downloads the PDF creation log file for the given vulnerability.
    """
    return deliver_report_file(
        session=session,
        user=current_user,
        project_id=project_id,
        report_id=report_id,
        report_section_id=section_id,
        vulnerability_id=vulnerability_id,
        delivery_fn=download_tex
    )
