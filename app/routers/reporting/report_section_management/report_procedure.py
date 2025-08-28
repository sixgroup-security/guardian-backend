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
from typing import Annotated, Optional
from fastapi import Depends, APIRouter, Security, status, Body
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum, update_attributes, StatusMessage, StatusEnum, InvalidDataError
from schema.reporting.report_section_management.report_procedure import (
    ReportProcedure, ReportProcedureRead, ReportProcedureUpdate
)
from routers.project import check_access_permission, get_project
from routers.reporting.report_section_management.report_section_playbook import API_REPORT_SECTION_PLAYBOOKS_PREFIX
from routers.user import get_current_active_user, User

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_REPORT_PROCEDURE_SUFFIX = "/{playbook_id}/sections/{playbook_section_id}/procedures"
API_REPORT_PROCEDURE_PREFIX = API_REPORT_SECTION_PLAYBOOKS_PREFIX + API_REPORT_PROCEDURE_SUFFIX

router = APIRouter(
    prefix=API_REPORT_PROCEDURE_PREFIX,
    tags=["report"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("/{procedure_id}", response_model=Optional[ReportProcedureRead])
def read_report_procedure(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_read.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    playbook_id: UUID,
    playbook_section_id: UUID,
    procedure_id: UUID
):
    """
    Returns a report procedure in the given report section.
    """
    check_access_permission(current_user, project)
    try:
        result = project.get_item(
            report_id=report_id,
            report_section_id=section_id,
            playbook_id=playbook_id,
            playbook_section_id=playbook_section_id,
            procedure_id=procedure_id
        )
        return result if result else {}
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{procedure_id}", response_model=StatusMessage)
def update_report_procedure(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: UUID,
    report_id: UUID,
    section_id: UUID,
    playbook_id: UUID,
    playbook_section_id: UUID,
    procedure_id: UUID,
    procedure: Annotated[ReportProcedureUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a report procedure in the given report section.
    """
    project = get_project(project_id, session)
    check_access_permission(current_user, project)
    try:
        current = project.get_item(
            report_id=report_id,
            report_section_id=section_id,
            playbook_id=playbook_id,
            playbook_section_id=playbook_section_id,
            procedure_id=procedure_id
        )
        if current:
            update_attributes(target=current, source=procedure, source_model=ReportProcedure)
            session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Procedure successfully updated."
        )
    except Exception as e:
        raise InvalidDataError(str(e))
