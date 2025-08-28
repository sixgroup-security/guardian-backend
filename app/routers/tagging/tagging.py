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

from typing import Annotated, List
from fastapi import Body, Depends, APIRouter, Security
from sqlalchemy import and_
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import InvalidDataError, ApiPermissionEnum
from schema.tagging import Tag, TagLookup, TagCreate, TagCategoryEnum
from routers.user import get_current_active_user, User

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_TAGGING_SUFFIX = "/tags"
API_TAGGING_PREFIX = API_PREFIX + API_TAGGING_SUFFIX


router = APIRouter(
    prefix=API_TAGGING_PREFIX,
    tags=["tagging"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def check_tag(tag: TagCreate, min_length: int, max_length: int):
    """
    Check if the given tag is valid.
    """
    if not min_length <= len(tag.name) <= max_length:
        raise InvalidDataError(f"The tag name length must be between {min_length} and {max_length} characters.")


def create_tag(
        session: Session,
        tag: Tag,
        categories: List[TagCategoryEnum],
        min_length: int = 2,
        max_length: int = 15
) -> Tag:
    """
    Add given tag to database if does not already exist.
    """
    try:
        result = (session.query(Tag)
                  .filter(and_(Tag.name == tag.name, Tag.categories.contains(categories)))
                  .order_by(Tag.name).one_or_none())
        if not result:
            check_tag(tag, min_length=min_length, max_length=max_length)
            result = Tag(**tag.model_dump(), categories=set(categories))
            session.add(result)
            session.commit()
            session.refresh(result)
        return result
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/projects/general", response_model=List[TagLookup])
def read_project_general(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all general project tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.general])) \
        .order_by(Tag.name).all()


@router.post("/projects/general", response_model=TagLookup)
def create_project_general(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new general project tag.
    """
    return create_tag(session=session, tag=tag, categories=[TagCategoryEnum.project, TagCategoryEnum.general])


@router.get("/projects/reasons", response_model=List[TagLookup])
def read_project_test_purposes(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all project test reasons.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.test_reason])) \
        .order_by(Tag.name).all()


@router.post("/projects/reasons", response_model=TagLookup)
def create_project_test_purposes(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new project test reason.
    """
    return create_tag(session=session, tag=tag, categories=[TagCategoryEnum.project, TagCategoryEnum.test_reason])


@router.get("/projects/environments", response_model=List[TagLookup])
def read_project_test_environments(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all project testing environments.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.environment])) \
        .order_by(Tag.name).all()


@router.post("/projects/environments", response_model=TagLookup)
def create_project_test_environment(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new project test environment.
    """
    return create_tag(session=session, tag=tag, categories=[TagCategoryEnum.project, TagCategoryEnum.environment])


@router.get("/projects/classifications", response_model=List[TagLookup])
def read_project_classifications(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all project classifications.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.project, TagCategoryEnum.classification])) \
        .order_by(Tag.name).all()


@router.post("/projects/classifications", response_model=TagLookup)
def create_project_classifications(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new project classifications.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[TagCategoryEnum.project, TagCategoryEnum.application, TagCategoryEnum.classification]
    )


@router.get("/measures/general", response_model=List[TagLookup])
def read_measure_tags(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.measure_tag_read.name]
    )],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all measure tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.measure, TagCategoryEnum.general])) \
        .order_by(Tag.name).all()


@router.post("/measures/general", response_model=TagLookup)
def create_measure_tag(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.measure_tag_create.name]
    )],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a measure tag.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[
            TagCategoryEnum.vulnerability_template,
            TagCategoryEnum.procedure,
            TagCategoryEnum.measure,
            TagCategoryEnum.general
        ],
        min_length=3,
        max_length=30
    )


@router.get("/test-procedure/general", response_model=List[TagLookup])
def read_test_procedure_tags(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.test_procedure_tag_read.name]
    )],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all test procedure tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.procedure, TagCategoryEnum.general])) \
        .order_by(Tag.name).all()


@router.post("/test-procedure/general", response_model=TagLookup)
def create_test_procedure_tag(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.test_procedure_tag_create.name]
    )],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a test procedure tag.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[
            TagCategoryEnum.vulnerability_template,
            TagCategoryEnum.procedure,
            TagCategoryEnum.measure,
            TagCategoryEnum.general
        ],
        min_length=3,
        max_length=30
    )


@router.get("/vulnerabilities/general", response_model=List[TagLookup])
def read_vulnerability_template_tags(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.vulnerability_template_tag_read.name]
    )],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all vulnerablity template tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.vulnerability_template, TagCategoryEnum.general])) \
        .order_by(Tag.name).all()


@router.post("/vulnerabilities/general", response_model=TagLookup)
def create_vulnerability_template_tag(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.vulnerability_template_tag_create.name]
    )],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a vulnerability template tag.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[
            TagCategoryEnum.vulnerability_template,
            TagCategoryEnum.procedure,
            TagCategoryEnum.measure,
            TagCategoryEnum.general
        ],
        min_length=3,
        max_length=30
    )


@router.get("/vulnerabilities/cwe", response_model=List[TagLookup])
def read_cwe_categories(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.vulnerability_template_tag_read.name]
    )],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all CWE categories.

    We have to keep this REST API endpoint for backward compatibility reasons.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.procedure, TagCategoryEnum.cwe_category])) \
        .order_by(Tag.name).all()


@router.get("/applications/general", response_model=List[TagLookup])
def read_application_general(
    _: Annotated[User, Security(
        get_current_active_user,
        scopes=[ApiPermissionEnum.application_tag_read.name]
    )],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all general application tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.general])) \
        .order_by(Tag.name).all()


@router.post("/applications/general", response_model=TagLookup)
def create_application_general(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new general application tag.
    """
    return create_tag(session=session, tag=tag, categories=[TagCategoryEnum.application, TagCategoryEnum.general])


@router.get("/applications/inventory", response_model=List[TagLookup])
def read_application_inventory(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all inventory application tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.inventory])) \
        .order_by(Tag.name).all()


@router.post("/applications/inventory", response_model=TagLookup)
def create_application_inventory(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new general application tag.
    """
    return create_tag(session=session, tag=tag, categories=[TagCategoryEnum.application, TagCategoryEnum.inventory])


@router.get("/applications/classification", response_model=List[TagLookup])
def read_application_classification(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all classification application tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.classification])) \
        .order_by(Tag.name).all()


@router.post("/applications/classification", response_model=TagLookup)
def create_application_classification(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new classification application tag.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[TagCategoryEnum.project, TagCategoryEnum.application, TagCategoryEnum.classification]
    )


@router.get("/applications/deployment-model", response_model=List[TagLookup])
def read_application_deployment_model(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all deployment model tags.
    """
    return session.query(Tag) \
        .filter(Tag.categories.contains([TagCategoryEnum.application, TagCategoryEnum.deployment_model])) \
        .order_by(Tag.name).all()


@router.post("/applications/deployment-model", response_model=TagLookup)
def create_application_deployment_model(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.application_tag_create.name])],
    tag: Annotated[TagCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new deployment model tag.
    """
    return create_tag(
        session=session,
        tag=tag,
        categories=[TagCategoryEnum.application, TagCategoryEnum.deployment_model]
    )
