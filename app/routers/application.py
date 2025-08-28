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
from sqlalchemy import and_, text
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import (
    ApiPermissionEnum, get_by_id, update_database_record, get_all, StatusMessage, StatusEnum, NotFoundError
)
from schema.country import Country
from schema.tagging import Tag, TagCategoryEnum
from schema.project_comment import ProjectComment
from schema.project import ProjectType, Project, ProjectState, ProjectRead
from schema.application import (
    Application, ApplicationRead, ApplicationCreate, ApplicationUpdate, ApplicationLookup,
    ApplicationProjectCreate, ApplicationProject
)
from routers.user import User, get_current_active_user, get_logger
from core import ExceptionWrapper

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_APPLICATION_SUFFIX = "/applications"
API_APPLICATION_PREFIX = API_PREFIX + API_APPLICATION_SUFFIX


router = APIRouter(
    prefix=API_APPLICATION_PREFIX,
    tags=["application"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def get_application(application_id: UUID, session: Annotated[Session, Depends(get_db)]) -> Application:
    """
    Get an application by its ID.
    """
    return get_by_id(session, Application, application_id)


def add_tags(
    session: Session,
    application: Application,
    general_tags: List[str],
    inventory_tags: List[str],
    classification_tags: List[str],
    deployment_model_tags: List[str],
):
    # TODO: Implement unittest.
    application.general_tags = session.query(Tag) \
        .filter(and_(Tag.id.in_(general_tags),
                     Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.general]))).all()
    application.inventory_tags = session.query(Tag) \
        .filter(and_(Tag.id.in_(inventory_tags),
                     Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.inventory]))).all()
    application.classification_tags = session.query(Tag) \
        .filter(and_(Tag.id.in_(classification_tags),
                     Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.classification]))).all()
    application.deployment_model_tags = session.query(Tag) \
        .filter(and_(Tag.id.in_(deployment_model_tags),
                     Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.deployment_model]))).all()


@router.get("")
def read_applications(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all applications.
    """
    # Due to the high amount of data, we let the database create the JSON object for us. Compiling the JSON object with
    # SQLAlchemy ORM and Pydantic takes up to a minute to compile the entire response.
    sql = """
        WITH ongoing_projects AS (
            SELECT a.id, p.year, COUNT(*) AS count FROM project p
            INNER JOIN applicationproject m ON m.project_id = p.id
            INNER JOIN application a ON m.application_id = a.id
            WHERE p.state NOT IN ('backlog', 'completed', 'cancelled', 'archived')
            GROUP BY a.id, p.year
        )
        SELECT
        json_agg(
            json_build_object(
                'id', a.id,
                'application_id', a.application_id,
                'name', a.name,
                'pentest_periodicity', a.pentest_periodicity,
                'state', CASE
                            WHEN a.state IS NULL THEN NULL
                            WHEN a.state = 'planned' THEN 0
                            WHEN a.state = 'development' THEN 10
                            WHEN a.state = 'production' THEN 20
                            WHEN a.state = 'decommissioned' THEN 30
                            ELSE -1
                        END,
                'in_scope', a.in_scope,
                'manual_pentest_periodicity', a.manual_pentest_periodicity,
                'periodicity_parameter', CASE
                                    WHEN a.periodicity_parameter IS NULL THEN NULL
                                    WHEN a.periodicity_parameter = 'manual' THEN 10
                                    WHEN a.periodicity_parameter = 'out_of_scope' THEN 20
                                    WHEN a.periodicity_parameter = 'decommissioned' THEN 100
                                    ELSE -1
                                END,
                'periodicity_details', a.periodicity_details,
                'description', a.description,
                'owner', CHOOSE_VALUE(owner.id IS NULL, NULL, json_build_object('id', owner.id, 'name', owner.name)),
                'manager', CHOOSE_VALUE(manager.id IS NULL, NULL, json_build_object('id', manager.id, 'name', manager.name)),
                'last_pentest', a.last_pentest,
                'next_pentest', a.next_pentest,
                'overdue', get_application_overdue_value(a),
                'inventory_tags', CHOOSE_VALUE(inventorytag.id IS NULL, '[]', inventorytag.tags),
                'classification_tags', CHOOSE_VALUE(classificationtag.id IS NULL, '[]', classificationtag.tags),
                'general_tags', CHOOSE_VALUE(generaltag.id IS NULL, '[]', generaltag.tags),
                'deployment_model_tags', CHOOSE_VALUE(deploymentmodeltag.id IS NULL, '[]', deploymentmodeltag.tags),
                'pentest_this_year', a.pentest_this_year
            )
        )
        FROM application a
        LEFT JOIN entity owner ON a.owner_id = owner.id
        LEFT JOIN entity manager ON a.manager_id = manager.id
        LEFT JOIN (
            SELECT
                at.id AS id,
                json_agg(
                    json_build_object(
                        'id', t.id,
                        'name', t.name
                    )
                ) AS tags
            FROM tag t
            INNER JOIN tagapplicationinventory tai ON t.id = tai.tag_id
            INNER JOIN application at ON at.id = tai.application_id
            GROUP BY at.id
        ) inventorytag ON inventorytag.id = a.id
        LEFT JOIN (
            SELECT
                at.id AS id,
                json_agg(
                    json_build_object(
                        'id', t.id,
                        'name', t.name
                    )
                ) AS tags
            FROM tag t
            INNER JOIN tagapplicationclassification tac ON t.id = tac.tag_id
            INNER JOIN application at ON at.id = tac.application_id
            GROUP BY at.id
        ) classificationtag ON classificationtag.id = a.id
        LEFT JOIN (
            SELECT
                at.id AS id,
                json_agg(
                    json_build_object(
                        'id', t.id,
                        'name', t.name
                    )
                ) AS tags
            FROM tag t
            INNER JOIN tagapplicationgeneral tag ON t.id = tag.tag_id
            INNER JOIN application at ON at.id = tag.application_id
            GROUP BY at.id
        ) generaltag ON generaltag.id = a.id
        LEFT JOIN (
            SELECT
                at.id AS id,
                json_agg(
                    json_build_object(
                        'id', t.id,
                        'name', t.name
                    )
                ) AS tags
            FROM tag t
            INNER JOIN tagapplicationdeploymentmodel tag ON t.id = tag.tag_id
            INNER JOIN application at ON at.id = tag.application_id
            GROUP BY at.id
        ) deploymentmodeltag ON deploymentmodeltag.id = a.id
        LEFT JOIN ongoing_projects op ON a.id = op.id AND EXTRACT(YEAR FROM NOW()) = op.year
    """.strip()
    result = session.execute(text(sql))
    applications = result.scalar_one_or_none()
    return applications if applications else []


@router.get("/lookup", response_model=List[ApplicationLookup])
def read_application_lookup(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns a summary for all applications.
    """
    result = get_all(session, Application).order_by(Application.application_id).all()
    return result


@router.get("/{application_id}", response_model=ApplicationRead)
def read_application(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_read.name])],
    application: Annotated[UUID, Depends(get_application)]
):
    """
    Returns an application by its ID.
    """
    return application


@router.get("/{application_id}/projects", response_model=List[ProjectRead])
def read_application_projects(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_project_read.name])],
    application: Annotated[UUID, Depends(get_application)],
    session: Session = Depends(get_db)
):
    """
    Returns all projects associated with a given application.
    """
    projects = []
    for item in session.query(Application).filter(Application.id == application.id).all():
        projects.extend(item.projects)
    return projects


@router.delete("/{application_id}", response_model=StatusMessage)
def delete_application(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_delete.name])],
    application: Annotated[UUID, Depends(get_application)],
    session: Session = Depends(get_db)
):
    """
    Deletes an application by its ID.
    """
    try:
        session.delete(application)
        session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"Application successfully deleted."
        )
    except Exception as e:
        raise ExceptionWrapper(e)


@router.post("", response_model=ApplicationRead)
def create_application(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_create.name])],
    application: Annotated[ApplicationCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new application.
    """
    try:
        # Input validation
        if application.manual_pentest_periodicity and len((application.periodicity_details or "").strip()) == 0:
            raise ValueError("Periodicity Details is mandatory if Manual PT Periodicity is set.")
        general_tags = list(application.general_tags) if application.general_tags else []
        inventory_tags = list(application.inventory_tags) if application.inventory_tags else []
        classification_tags = list(application.classification_tags) if application.classification_tags else []
        deployment_model_tags = list(application.deployment_model_tags) if application.deployment_model_tags else []
        application_json = application.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude={"general_tags", "inventory_tags", "classification_tags", "deployment_model_tags"}
        )
        new = Application(**application_json)
        session.add(new)
        add_tags(
            session=session,
            application=new,
            general_tags=general_tags,
            inventory_tags=inventory_tags,
            classification_tags=classification_tags,
            deployment_model_tags=deployment_model_tags
        )
        session.commit()
        session.refresh(new)
        return new
    except Exception as e:
        raise ExceptionWrapper(e)


@router.post("/projects/create", response_model=StatusMessage)
def batch_create_projects(
    current_user: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.application_project_batch_create.name]
    )],
    batch: Annotated[ApplicationProjectCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Batch creates projects based on the given application information.
    """
    try:
        count = len(batch.applications)
        project_type = ProjectType(batch.type)
        user = get_by_id(session, User, current_user.id)
        location = get_by_id(session, Country, batch.location_id)
        for application_id in batch.applications:
            # We obtain the application
            application = get_by_id(session, Application, application_id)
            # We obtain the manager via the application's owner
            manager_id = application.owner.manager_id if application.owner and application.owner.manager_id else None
            project = Project(
                name=application.name,
                start_date=batch.start,
                location=location,
                state=ProjectState.planning,
                project_type=project_type,
                manager_id=manager_id,
                customer_id=application.owner_id
            )
            session.add(project)
            session.add(ApplicationProject(application=application, project=project))
            session.add(ProjectComment(
                project=project,
                user=user,
                comment="Project was automatically created via batch creation."
            ))
        session.commit()
        plural = "s" if count > 0 else ""
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"{count} project{plural} successfully created."
        )
    except Exception as e:
        raise ExceptionWrapper(e)


@router.put("", response_model=ApplicationRead)
def update_application(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[ApplicationUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Update an application by its ID.
    """
    try:
        # Input validation
        if item.manual_pentest_periodicity and len((item.periodicity_details or "").strip()) == 0:
            raise ValueError("Periodicity Details is mandatory if Manual PT Periodicity is set.")
        general_tags = list(item.general_tags) if item.general_tags else []
        inventory_tags = list(item.inventory_tags) if item.inventory_tags else []
        classification_tags = list(item.classification_tags) if item.classification_tags else []
        deployment_model_tags = list(item.deployment_model_tags) if item.deployment_model_tags else []
        # We obtain the project from the database and update it.
        result = update_database_record(
            session=session,
            source=item,
            query_model=Application,
            source_model=ApplicationUpdate,
            commit=False,
            exclude={"general_tags", "inventory_tags", "classification_tags", "deployment_model_tags"}
        )
        add_tags(
            session=session,
            application=result,
            general_tags=general_tags,
            inventory_tags=inventory_tags,
            classification_tags=classification_tags,
            deployment_model_tags=deployment_model_tags
        )
        session.commit()
        session.refresh(result)
        return result
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise ExceptionWrapper(e)
