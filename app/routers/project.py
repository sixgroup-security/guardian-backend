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
# along with MyAwesomeProject. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
from uuid import UUID
from typing import Annotated, List
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import (
    GuardianRoleEnum, ApiPermissionEnum, get_by_id, update_database_record, StatusEnum, StatusMessage,
    InvalidDataError, NotFoundError
)
from schema.tagging import Tag, TagCategoryEnum
from schema.entity import Entity, EntityRoleEnum
from schema.project_user import ProjectTester
from schema.project_comment import ProjectComment
from schema.project import Project, ProjectRead, ProjectCreate, ProjectUpdate, model_dump as project_model_dump
from schema.application import Application
from routers.user import User, get_current_active_user, get_logger
from routers.util import get_project_years

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_PROJECT_SUFFIX = "/projects"
API_PROJECT_PREFIX = API_PREFIX + API_PROJECT_SUFFIX


router = APIRouter(
    prefix=API_PROJECT_PREFIX,
    tags=["project"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def get_project(project_id: UUID, session: Annotated[Session, Depends(get_db)]) -> Project:
    """
    Get a project by its ID.
    """
    return get_by_id(session, Project, project_id)


def check_manager_id(session: Session, manager_id: UUID):
    """
    Checks if the given manager ID is valid.
    """
    if manager_id is None:
        return
    count = session.query(User).filter(and_(User.id == manager_id,
                                            User.roles.contains([GuardianRoleEnum.manager]))).count()
    if count == 0:
        raise InvalidDataError("Provided manager is invalid. Make sure user exists and is a member of role Manager.")


def check_customer_id(session: Session, customer_id: UUID):
    """
    Checks if the given customer ID is valid.
    """
    if customer_id is None:
        return
    count = session.query(Entity).filter(and_(Entity.id == customer_id,
                                              Entity.role == EntityRoleEnum.customer)).count()
    if count == 0:
        raise InvalidDataError("Provided customer is invalid. Make sure user exists and is a member of role Customer.")


def check_provider_id(session: Session, provider_id: UUID):
    """
    Checks if the given provider ID is valid.
    """
    if provider_id is None:
        return
    count = session.query(Entity).filter(and_(Entity.id == provider_id,
                                              Entity.role == EntityRoleEnum.provider)).count()
    if count == 0:
        raise InvalidDataError("Provided provider is invalid. Make sure user exists and is a member of role Provider.")


def check_access_permission(current_user: User, project: Project):
    """
    Checks if the current user has permission to access the project,
    """
    # TODO: Implement permission check
    ...


def update_applications(session: Session, project: Project, application_ids: List[UUID]):
    """
    Updates the project's applications list with the given application IDs.
    """
    # Delete all applications that are not in the list of application IDs.
    for application in project.applications:
        if application.id not in application_ids:
            project.applications.remove(application)
    # Add all applications that are not in the project yet.
    new_applications = [item.id for item in project.applications]
    for application_id in application_ids:
        application = session.query(Application).filter_by(id=application_id).one_or_none()
        if application_id not in new_applications and application:
            project.applications.append(application)


def update_testers(session: Session, project: Project, tester_ids: List[UUID]):
    """
    Updates the project's testers list with the given tester IDs.
    """
    # Delete all testers that are not in the list of tester IDs.
    for tester in project.testers:
        if tester.id not in tester_ids:
            project.testers.remove(tester)
    # Add all testers that are not in the project yet.
    new_testers = [item.id for item in project.testers]
    for tester_id in tester_ids:
        tester = (session.query(User)
                  .filter(and_(User.id == tester_id,
                               or_(User.roles.contains([GuardianRoleEnum.pentester]),
                                   User.roles.contains([GuardianRoleEnum.leadpentester])))).one_or_none())
        if tester_id not in new_testers and tester:
            project.testers.append(tester)


def add_testers(session: Session, project: Project, tester_ids: List[UUID]):
    """
    Adds the given tester IDs to the project.
    """
    # We delete all existing project/tester relationships.
    for link in project.project_tester_links:
        session.delete(link)
    # We create the new links.
    for i in range(len(tester_ids)):
        tester_id = tester_ids[i]
        tester = session.query(User).filter_by(id=tester_id).one_or_none()
        # With this, we prevent user enumeration attacks.
        if tester:
            session.add(ProjectTester(project=project, user=tester))


def add_tags(
    session: Session,
    project: Project,
    tag_reason_ids: List[str],
    tag_environment_ids: List[str],
    tag_classification_ids: List[str],
    tag_general_ids: List[str],
):
    # De-duplicate general tag IDs.
    for tag_id in tag_general_ids:
        if tag_id in tag_reason_ids or tag_id in tag_environment_ids:
            tag_general_ids.remove(tag_id)
    # We delete all existing project/application relationships.
    # TODO: Implement unittest.
    project.reasons = session.query(Tag) \
        .filter(and_(Tag.id.in_(tag_reason_ids),
                     Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.test_reason]))).all()
    project.environments = session.query(Tag) \
        .filter(and_(Tag.id.in_(tag_environment_ids),
                     Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.environment]))).all()
    project.classifications = session.query(Tag) \
        .filter(and_(Tag.id.in_(tag_classification_ids),
                     Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.classification]))).all()
    tags = session.query(Tag) \
        .filter(and_(Tag.id.in_(tag_general_ids),
                     Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.general]))).all()
    # We perform de-duplication based on the tag name.
    items = {item.name: item for item in project.reasons + project.environments}
    project.tags = [item for item in tags if item.name not in items]


@router.get("")
def read_projects(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_read.name])],
    session: Annotated[Session, Depends(get_db)],
    year: str | None = None
):
    """
    Returns all projects.
    """
    # Due to the high amount of data, we let the database create the JSON object for us. Compiling the JSON object with
    # SQLAlchemy ORM and Pydantic takes up to a minute to compile the entire response.
    sql = """
        SELECT
        json_agg(
            json_build_object(
                'id', p.id,
                'project_id', get_project_id(p),
                'name', p.name,
                'project_type', CASE
                                    WHEN p.project_type IS NULL THEN NULL
                                    WHEN p.project_type = 'attack_modelling' THEN 10
                                    WHEN p.project_type = 'bug_bounty' THEN 20
                                    WHEN p.project_type = 'red_team_exercise' THEN 30
                                    WHEN p.project_type = 'penetration_test' THEN 40
                                    WHEN p.project_type = 'purple_team_exercise' THEN 50
                                    WHEN p.project_type = 'security_assessment' THEN 60
                                    ELSE -1
                                END,
                'state', CASE
                            WHEN p.state IS NULL THEN NULL
                            WHEN p.state = 'backlog' THEN 10
                            WHEN p.state = 'planning' THEN 20
                            WHEN p.state = 'scheduled' THEN 25
                            WHEN p.state = 'running' THEN 30
                            WHEN p.state = 'reporting' THEN 40
                            WHEN p.state = 'completed' THEN 50
                            WHEN p.state = 'cancelled' THEN 60
                            WHEN p.state = 'archived' THEN 70
                            ELSE -1
                        END,
                'start_date', p.start_date,
                'end_date', p.end_date,
                'completion_date', p.completion_date,
                'applications', CHOOSE_VALUE(application.project_id IS NULL, '[]', application.applications),
                'reasons', CHOOSE_VALUE(testreasontag.id IS NULL, '[]', testreasontag.tags),
                'environments', CHOOSE_VALUE(environmenttag.id IS NULL, '[]', environmenttag.tags),
                'classifications', CHOOSE_VALUE(classificationtag.id IS NULL, '[]', classificationtag.tags),
                'tags', CHOOSE_VALUE(generaltag.id IS NULL, '[]', generaltag.tags),
                'lead_tester', CHOOSE_VALUE(lead_tester.id IS NULL, NULL, json_build_object(
                    'id', lead_tester.id,
                    'label', lead_tester.full_name
                )),
                'manager', CHOOSE_VALUE(manager.id IS NULL, NULL, json_build_object(
                    'id', manager.id,
                    'label', manager.full_name
                )),
                'testers', CHOOSE_VALUE(tester.project_id IS NULL, '[]', tester.testers),
                'provider', CHOOSE_VALUE(provider.id IS NULL, NULL, json_build_object(
                    'id', provider.id,
                    'name', provider.name
                )),
                'customer', CHOOSE_VALUE(customer.id IS NULL, NULL, json_build_object(
                    'id', customer.id,
                    'name', customer.name
                )),
                'location', CHOOSE_VALUE(location.id IS NULL, NULL, json_build_object(
                    'id', location.id,
                    'name', location.name,
                    'country_code', location.code
                )),
                'reports', CHOOSE_VALUE(report.project_id IS NULL, '[]', report.reports),
                'comments', CHOOSE_VALUE(comment.project_id IS NULL, '[]', comment.comments)
            )
        )
    FROM project p
    LEFT JOIN "user" lead_tester ON lead_tester.id = p.lead_tester_id
    LEFT JOIN "user" manager ON manager.id = p.manager_id
    LEFT JOIN entity provider ON provider.id = p.provider_id
    LEFT JOIN entity customer ON customer.id = p.customer_id
    LEFT JOIN country location ON location.id = p.location_id
    LEFT JOIN (
        SELECT
            p.id AS project_id,
            json_agg(
                json_build_object(
                    'id', a.id,
                    'label', CONCAT(a.application_id, ' - ', a.name),
                    'app_id', a.application_id
                )
            ) AS applications
        FROM project p
        INNER JOIN applicationproject ap ON p.id = ap.project_id
        INNER JOIN application a ON a.id = ap.application_id
        GROUP BY p.id
    ) application ON application.project_id = p.id
    LEFT JOIN (
        SELECT
            pt.id AS id,
            json_agg(
                json_build_object(
                    'id', t.id,
                    'name', t.name
                )
            ) AS tags
        FROM tag t
        INNER JOIN tagprojecttestreason m ON t.id = m.tag_id
        INNER JOIN project pt ON pt.id = m.project_id
        GROUP BY pt.id
    ) testreasontag ON testreasontag.id = p.id
    LEFT JOIN (
        SELECT
            pt.id AS id,
            json_agg(
                json_build_object(
                    'id', t.id,
                    'name', t.name
                )
            ) AS tags
        FROM tag t
        INNER JOIN tagprojectenvironment m ON t.id = m.tag_id
        INNER JOIN project pt ON pt.id = m.project_id
        GROUP BY pt.id
    ) environmenttag ON environmenttag.id = p.id
    LEFT JOIN (
        SELECT
            pt.id AS id,
            json_agg(
                json_build_object(
                    'id', t.id,
                    'name', t.name
                )
            ) AS tags
        FROM tag t
        INNER JOIN tagprojectclassification m ON t.id = m.tag_id
        INNER JOIN project pt ON pt.id = m.project_id
        GROUP BY pt.id
    ) classificationtag ON classificationtag.id = p.id
    LEFT JOIN (
        SELECT
            pt.id AS id,
            json_agg(
                json_build_object(
                    'id', t.id,
                    'name', t.name
                )
            ) AS tags
        FROM tag t
        INNER JOIN tagprojectgeneral m ON t.id = m.tag_id
        INNER JOIN project pt ON pt.id = m.project_id
        GROUP BY pt.id
    ) generaltag ON generaltag.id = p.id
    LEFT JOIN (
        SELECT
            p.id AS project_id,
            json_agg(
                json_build_object(
                    'id', u.id,
                    'label', u.full_name
                )
            ) AS testers
        FROM project p
        INNER JOIN projecttester m ON p.id = m.project_id
        INNER JOIN "user" u ON u.id = m.user_id
        GROUP BY p.id
    ) tester ON tester.project_id = p.id
    LEFT JOIN (
        SELECT
            p.id AS project_id,
            json_agg(
                json_build_object(
                    'id', r.id,
                    'report_template', json_build_object(
                        'id', rt.id,
                        'name', rt.name
                    ),
                    'report_language', json_build_object(
                        'id', rl.id,
                        'name', rl.name,
                        'is_default', rl.is_default,
                        'language_code', rl.language_code,
                        'country_code', c.code
                    )
                )
            ) AS reports
        FROM project p
        INNER JOIN report r ON p.id = r.project_id
        INNER JOIN reporttemplate rt ON rt.id = r.report_template_id
        INNER JOIN reportlanguage rl ON rl.id = r.report_language_id
        INNER JOIN country c ON c.id = rl.country_id
        GROUP BY p.id
    ) report ON report.project_id = p.id
    LEFT JOIN (
        SELECT
            p.id AS project_id,
            json_agg(
                json_build_object(
                    'id', c.id,
                    'user', json_build_object(
                        'id', u.id,
                        'label', u.full_name
                    ),
                    'comment', c.comment,
                    'created_at', c.created_at
                ) ORDER BY c.created_at DESC
            ) AS comments
        FROM project p
        INNER JOIN projectcomment c ON c.project_id = p.id
        INNER JOIN "user" u ON c.user_id = u.id
        GROUP BY p.id
    ) comment ON comment.project_id = p.id
    WHERE EXTRACT(YEAR FROM p.start_date) = :year OR :all
    """
    if year is None or year == "All":
        result = session.execute(text(sql), {'year': 0, 'all': True})
        projects = result.scalar_one_or_none()
    elif year and year.isdigit():
        result = session.execute(text(sql), {'year': int(year), 'all': False})
        projects = result.scalar_one_or_none()
    else:
        projects = None
    return projects if projects else []


@router.get("/years", response_model=List[str])
def read_project_years(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all years with at least one project's start date.
    """
    return get_project_years(session)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_read.name])],
    project: Annotated[UUID, Depends(get_project)]
):
    """
    Returns a project by its ID.
    """
    check_access_permission(current_user, project)
    return project


@router.get("/{project_id}/reports", response_model=ProjectRead)
def read_project(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_read.name])],
    project: Annotated[UUID, Depends(get_project)]
):
    """
    Returns a project by its ID.
    """
    check_access_permission(current_user, project)
    return project


@router.delete("/{project_id}", response_model=StatusMessage)
def delete_project(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_delete.name])],
    project: Annotated[UUID, Depends(get_project)],
    db: Session = Depends(get_db)
):
    """
    Deletes a project by its ID.
    """
    check_access_permission(current_user, project)
    db.delete(project)
    db.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Record successfully deleted."
    )


@router.post("", response_model=ProjectRead)
def create_project(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_create.name])],
    item: Annotated[ProjectCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new project.
    """
    check_access_permission(current_user, item)
    try:
        # Check if the given manager ID is valid.
        # TODO: Implement unittests to test cases for check_manager_id, check_customer_id and check_provider_id
        check_manager_id(session, item.manager_id)
        check_customer_id(session, item.customer_id)
        check_provider_id(session, item.provider_id)
        # Obtain the foreign key IDs and then remove them from the item because the applications attribute is a
        # relationship property.
        application_ids = list(item.applications) if item.applications else []
        # Obtain the foreign key IDs and then remove them from the item because the testers attribute is a
        # relationship property.
        tester_ids = list(item.testers) if item.testers else []
        tag_reason_ids = list(item.reasons) if item.reasons else []
        tag_environment_ids = list(item.environments) if item.environments else []
        tag_classification_ids = list(item.classifications) if item.classifications else []
        tag_general_ids = list(item.tags) if item.tags else []
        # Create the new project.
        project_json = project_model_dump(item)
        new = Project(**project_json)
        session.add(new)
        # Add comment
        user = session.query(User).filter_by(id=current_user.id).one()
        comment = ProjectComment(comment=item.comment, user=user, project=new)
        session.add(comment)
        # Assign foreign keys
        update_testers(session, new, tester_ids)
        update_applications(session, new, application_ids)
        add_tags(session, new, tag_reason_ids, tag_environment_ids, tag_classification_ids, tag_general_ids)
        session.commit()
        session.refresh(new)
        return new
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("", response_model=ProjectRead)
def update_project(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_update.name])],
    item: Annotated[ProjectUpdate, Body],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    session: Session = Depends(get_db)
):
    """
    Update a project by its ID.
    """
    check_access_permission(current_user, item)
    try:
        # Check if the given manager ID is valid.
        # TODO: Implement unittests to test cases for check_manager_id, check_customer_id and check_provider_id
        check_manager_id(session, item.manager_id)
        check_customer_id(session, item.customer_id)
        check_provider_id(session, item.provider_id)
        # Obtain the foreign key IDs and then remove them from the item because applications is relationship property.
        application_ids = list(item.applications) if item.applications else []
        # Obtain the foreign key IDs and then remove them from the item because applications is relationship property.
        tester_ids = list(item.testers) if item.testers else []
        tag_reason_ids = list(item.reasons) if item.reasons else []
        tag_environment_ids = list(item.environments) if item.environments else []
        tag_classification_ids = list(item.classifications) if item.classifications else []
        tag_general_ids = list(item.tags) if item.tags else []
        # We obtain the project from the database and update it.
        result = update_database_record(
            session=session,
            source=item,
            source_model=ProjectUpdate,
            query_model=Project,
            commit=False,
            exclude={"applications", "testers", "reasons", "environments", "classifications", "tags"}
        )
        # Add comment
        user = session.query(User).filter_by(id=current_user.id).one()
        comment = ProjectComment(comment=item.comment, user=user, project=result)
        session.add(comment)
        # We delete all existing project/application relationships and create new ones.
        update_testers(session, result, tester_ids)
        update_applications(session, result, application_ids)
        add_tags(session, result, tag_reason_ids, tag_environment_ids, tag_classification_ids, tag_general_ids)
        session.commit()
        session.refresh(result)
        return result
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))
