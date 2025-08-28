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
from typing import Annotated, List, Dict
from fastapi import Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum, StatusMessage, StatusEnum, InvalidDataError
from schema.reporting.report import Report
from schema.reporting.report_language import ReportLanguage
from schema.reporting.report_section_management.report_procedure import ReportProcedure
from schema.reporting.report_section_management.playbook_section import PlaybookSection
from schema.reporting.report_section_management.report_section_playbook import (ReportSectionPlaybook)
from schema.reporting.vulnerability.test_procedure import TestProcedure
from schema.reporting.vulnerability.playbook import Playbook
from routers.user import get_current_active_user, User
from routers.project import check_access_permission, get_project
from routers.reporting.report_section_management.report_section import API_REPORT_SECTION_PREFIX
from core import InvalidPlaybookStructure

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

# /projects/{project_id}/reports/{report_id}/report-sections/{section_id}/playbooks/{playbook_id}
API_REPORT_SECTION_PLAYBOOKS_SUFFIX = "/{section_id}/playbooks"
API_REPORT_SECTION_PLAYBOOKS_PREFIX = API_REPORT_SECTION_PREFIX + API_REPORT_SECTION_PLAYBOOKS_SUFFIX

router = APIRouter(
    prefix=API_REPORT_SECTION_PLAYBOOKS_PREFIX,
    tags=["report"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def _check_playbook_structure(structure: Dict, language_code: str):
    if "type" not in structure:
        raise InvalidPlaybookStructure()
    elif structure["type"] == "container" and ("info" not in structure and (
            "title" not in structure["info"] or "description" not in structure["info"]) or
                                               "children" not in structure or
                                               language_code not in structure["info"]["title"] or
                                               language_code not in structure["info"]["description"]):
        raise InvalidPlaybookStructure()
    elif structure["type"] == "procedure" and "id" not in structure:
        raise InvalidPlaybookStructure()


def create_playbook(session: Session, report: Report, playbook: ReportSectionPlaybook, structure: Dict):
    """
    Creates the given playbook and assigns it to the given report section.

    :param session: The database session used to interact with the database.
    :param report: The current report.
    :param playbook: Relationship object between the report section and playbook template.
    :param structure: The tree structure of the playbook
    :return:
    """
    language_code = report.report_language.language_code
    if not isinstance(structure, list):
        raise InvalidPlaybookStructure()
    order = 1
    for content in structure:
        # Check if the structure is valid
        if not isinstance(content, dict):
            raise InvalidPlaybookStructure()
        _check_playbook_structure(content, language_code)
        if content["type"] == "container":
            # Create a playbook's section
            parent = PlaybookSection(
                name=content["info"]["title"][language_code],
                description=content["info"]["description"][language_code],
                playbook=playbook,
                order=order
            )
            session.add(parent)
            _create_playbook(
                session=session,
                report=report,
                language=report.report_language,
                parent=parent,
                parent_node=content
            )
            order += 10
        else:
            raise InvalidPlaybookStructure()


def _create_playbook(
        session: Session,
        report: Report,
        parent: PlaybookSection,
        language: ReportLanguage,
        parent_node: Dict
):
    """
    Creates the given playbook and assigns.
    """
    if "children" in parent_node:
        order_playbook_section = 1
        order_report_procedure = 1
        for content in parent_node["children"]:
            # Check if the structure is valid
            if not isinstance(content, dict):
                raise InvalidPlaybookStructure()
            _check_playbook_structure(content, language.language_code)
            node_type = content["type"]
            if node_type == "container":
                result = PlaybookSection(
                    name=content["info"]["title"][language.language_code],
                    description=content["info"]["description"][language.language_code],
                    order=order_playbook_section,
                    parent=parent
                )
                session.add(result)
                # Parse all child nodes
                _create_playbook(session, report, result, language, content)
                order_playbook_section += 10
            elif node_type == "procedure":
                procedure = session.query(TestProcedure).filter_by(id=content["id"]).one_or_none()
                if not procedure:
                    raise InvalidPlaybookStructure()
                result = ReportProcedure.clone_from_template(
                    language=language,
                    template=procedure,
                    order=order_report_procedure,
                    report=report,
                    section=parent,
                )
                session.add(result)
                order_report_procedure += 10
            else:
                raise InvalidPlaybookStructure()
    else:
        raise InvalidPlaybookStructure()


@router.post("", response_model=StatusMessage)
def create_report_section_playbook(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    playbook_ids: List[UUID],
    session: Session = Depends(get_db)
):
    """
    Creates a new playbook in the given report section.
    """
    check_access_permission(current_user, project)
    try:
        commit = False
        report = project.get_report(report_id, must_exist=True)
        section = report.get_section(section_id)
        if section:
            order = (max([item.order for item in section.playbooks]) if section.playbooks else 0) + 10
            for item in playbook_ids:
                # Check if mapping already exists
                mapping = (session.query(ReportSectionPlaybook)
                           .filter_by(section_id=section_id, playbook_id=item).first())
                playbook = session.query(Playbook).filter_by(id=item).one_or_none()
                if not mapping and playbook:
                    result = ReportSectionPlaybook(
                        section_id=section.id,
                        playbook_id=playbook.id,
                        name=playbook.name,
                        order=order
                    )
                    session.add(result)
                    # Add the playbook to the database by recursively publishing all tables.
                    create_playbook(
                        session=session,
                        report=report,
                        playbook=result,
                        structure=playbook.structure
                    )
                    order += 10
                    commit = True
            if commit:
                session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Playbook successfully added."
        )
    except ValueError as ex:
        logger.exception(ex)
    except Exception as e:
        raise InvalidDataError(str(e))


@router.delete("/{playbook_id}", response_model=StatusMessage)
def delete_report_section_playbook(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    playbook_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Deletes a playbook in the given report section..
    """
    check_access_permission(current_user, project)
    try:
        playbook = project.get_item(report_id=report_id, report_section_id=section_id, playbook_id=playbook_id)
        if playbook:
            session.delete(playbook)
            session.commit()
        return StatusMessage(status=status.HTTP_200_OK,
                             severity=StatusEnum.success,
                             message=f"Playbook successfully deleted.")
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{playbook_id}/move-down", response_model=StatusMessage)
def move_report_section_playbook_down(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    playbook_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Changes the order of a playbook.
    """
    check_access_permission(current_user, project)
    try:
        playbook = project.get_item(report_id=report_id, report_section_id=section_id, playbook_id=playbook_id)
        playbooks = list(
            filter(lambda x: x.order > playbook.order, sorted(playbook.section.playbooks, key=lambda x: x.order))
        )
        if playbooks:
            current_order = playbook.order
            playbook.order = playbooks[0].order
            playbooks[0].order = current_order
            session.commit()
        return StatusMessage(status=status.HTTP_200_OK,
                             severity=StatusEnum.success,
                             message=f"Playbook successfully deleted.")
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("/{playbook_id}/move-up", response_model=StatusMessage)
def move_report_section_playbook_up(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project: Annotated[UUID, Depends(get_project)],
    report_id: UUID,
    section_id: UUID,
    playbook_id: UUID,
    session: Session = Depends(get_db)
):
    """
    Changes the order of a playbook.
    """
    check_access_permission(current_user, project)
    try:
        playbook = project.get_item(report_id=report_id, report_section_id=section_id, playbook_id=playbook_id)
        playbooks = list(
            filter(lambda x: x.order < playbook.order, sorted(playbook.section.playbooks, key=lambda x: x.order))
        )
        if playbooks:
            current_order = playbook.order
            playbook.order = playbooks[-1].order
            playbooks[-1].order = current_order
            session.commit()
        return StatusMessage(status=status.HTTP_200_OK,
                             severity=StatusEnum.success,
                             message=f"Playbook successfully deleted.")
    except Exception as e:
        raise InvalidDataError(str(e))
