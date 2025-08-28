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
from typing import Annotated, Dict, List
from sqlmodel import SQLModel
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import (
    ApiPermissionEnum, get_by_id, update_database_record, StatusMessage, StatusEnum, ProjectType,
    InvalidDataError, update_language_fields, NotFoundError
)
from schema.reporting.report_template import (
    ReportTemplate, ReportTemplateCreate, ReportTemplateLanguage, ReportTemplateRead, ReportTemplateUpdate,
    ReportTemplateLookup
)
from routers.user import User, get_current_active_user, get_logger

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_TEMPLATE_SUFFIX = "/templates"
API_TEMPLATE_PREFIX = API_PREFIX + API_TEMPLATE_SUFFIX


router = APIRouter(
    prefix=API_TEMPLATE_PREFIX,
    tags=["report template"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def post_process_report_template_language(
        session: Session,
        report_template: SQLModel,
        **kwargs: Dict[str, str]
):
    """
    Process the language-specific details of a report template.
    """
    # Define function that creates a new language details object.
    def create_object(parent_object: SQLModel, language: SQLModel, **kwargs: Dict[str, str]):
        return ReportTemplateLanguage(
            language=language,
            report_template=parent_object,
            **kwargs
        )
    # Create/update the language details table for the report template.
    update_language_fields(
        session=session,
        parent_object=report_template,
        create_object=create_object,
        **kwargs
    )


def check_report_template(template: ReportTemplateCreate | ReportTemplateUpdate):
    """
    Checks if the given report template is valid.
    """
    # Ensure valid project type is provided
    if template.version is None:
        raise InvalidDataError("Version is required.")
    if template.executive_summary is None or len(template.executive_summary) == 0:
        raise InvalidDataError("Executive summary is required.")
    if template.prefix_section_text is None or len(template.prefix_section_text) == 0:
        raise InvalidDataError("Prefix section text is required.")
    if template.postfix_section_text is None or len(template.postfix_section_text) == 0:
        raise InvalidDataError("Postfix section text is required.")


def get_report_template_by_id(template_id: UUID, session: Annotated[Session, Depends(get_db)]) -> SQLModel:
    """
    Get a report template by its ID.
    """
    return get_by_id(session, ReportTemplate, template_id)


def get_report_templates(session: Session, project_type: ProjectType) -> List[ReportTemplate]:
    """
    Method returns all measures for specific project types.
    """
    return session.query(ReportTemplate).filter_by(project_type=project_type).order_by(ReportTemplate.name).all()


@router.get("/pentest", response_model=List[ReportTemplateRead])
def read_pentest_report_templates(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_template_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all penetration testing report templates.
    """
    return get_report_templates(session, ProjectType.penetration_test)


@router.get("/pentest/lookup", response_model=List[ReportTemplateLookup])
def read_pentest_report_templates(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_template_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns a summary for all penetration testing report templates.
    """
    return get_report_templates(session, ProjectType.penetration_test)


@router.delete("/pentest/{template_id}", response_model=StatusMessage)
def delete_pentest_report_template(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_template_delete.name])],
    report_template: Annotated[UUID, Depends(get_report_template_by_id)],
    session: Session = Depends(get_db)
):
    """
    Deletes a penetration testing report template by its ID.
    """
    session.delete(report_template)
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Record successfully deleted."
    )


@router.post("/pentest", response_model=ReportTemplateRead)
def create_pentest_report_template(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_template_create.name])],
    template: Annotated[ReportTemplateCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a penetration testing report template by its ID.
    """
    try:
        check_report_template(template)
        # Create the report template
        result = ReportTemplate(**template.model_dump(), project_type=ProjectType.penetration_test)
        session.add(result)
        # Create the language-specific details of the report template
        post_process_report_template_language(
            session,
            result,
            executive_summary=template.executive_summary,
            prefix_section_text=template.prefix_section_text,
            postfix_section_text=template.postfix_section_text,
            summary_template=template.summary_template
        )
        session.commit()
        session.refresh(result)
        return result
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/pentest", response_model=ReportTemplateRead)
def update_pentest_report_template(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_template_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[ReportTemplateUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a penetration testing report template.
    """
    try:
        check_report_template(item)
        # Update the report template
        result = update_database_record(
            session=session,
            source=item,
            source_model=ReportTemplateUpdate,
            query_model=ReportTemplate,
            commit=False
        )
        # Update the language-specific details of the report template
        post_process_report_template_language(
            session, result,
            executive_summary=item.executive_summary,
            prefix_section_text=item.prefix_section_text,
            postfix_section_text=item.postfix_section_text,
            summary_template=item.summary_template
        )
        session.commit()
        session.refresh(result)
        return result
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))
