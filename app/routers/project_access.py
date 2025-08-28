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

from uuid import UUID
from typing import List
from typing import Annotated
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import GuardianRoleEnum, ApiPermissionEnum, StatusMessage, StatusEnum, InvalidDataError
from schema.project_user import (
    ProjectAccess, ProjectAccessRead, ProjectAccessCreate, ProjectAccessUpdate, PermissionEnum
)
from routers.user import User, get_user, get_current_active_user
from routers.project import API_PROJECT_PREFIX, get_project
from core import DataNotFoundError

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

router = APIRouter(
    prefix=API_PROJECT_PREFIX,
    tags=["project access"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        500: {"description": "Internal Server Error"}
    }
)


def verify_access(session: Session, access: ProjectAccess) -> User:
    """
    This method checks if the given user ID is valid for getting project access assigned.
    """
    user = session.query(User).filter(and_(User.id == access.user_id,
                                            or_(
                                                User.roles.contains([GuardianRoleEnum.customer]),
                                                User.roles.contains([GuardianRoleEnum.leadpentester]),
                                                User.roles.contains([GuardianRoleEnum.pentester]),
                                            ))).first()
    if user is None:
        raise InvalidDataError("Provided user is invalid. Make sure user exists and is a member of role Customer, "
                               "SuperTester or PenTester.")
    if (GuardianRoleEnum.customer in user.roles and
            (len(access.permissions) > 1 or PermissionEnum.read not in access.permissions)):
        raise InvalidDataError("Customers can only have read permissions.")
    if access.permissions is None or len(access.permissions) == 0:
        raise InvalidDataError("Provided permissions are invalid. Make sure permissions are not empty.")
    return user


@router.get("/{project_id}/access", response_model=List[ProjectAccessRead])
def read_project_access_permissions(
    project: Annotated[UUID, Depends(get_project)],
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.project_access_read.name])],
):
    """
    Returns a project's access permissions.
    """
    return session.query(ProjectAccess).filter_by(project_id=project.id).all()


@router.delete("/{project_id}/access/{user_id}", response_model=StatusMessage)
def delete_project_access_permission(
    project: Annotated[UUID, Depends(get_project)],
    user: Annotated[UUID, Depends(get_user)],
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.project_access_delete.name])],
):
    """
    Deletes a user's project access permissions.
    """
    access = session.query(ProjectAccess).filter_by(project_id=project.id, user_id=user.id).first()
    if not access:
        raise DataNotFoundError()
    session.delete(access)
    session.commit()
    return StatusMessage(status=status.HTTP_200_OK,
                         severity=StatusEnum.success,
                         message=f"Record successfully deleted.")


@router.post("/{project_id}/access", response_model=ProjectAccessRead)
def create_project_access_permission(
    project: Annotated[UUID, Depends(get_project)],
    access: Annotated[ProjectAccessCreate, Body(...)],
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.project_access_create.name])],
):
    """
    Creates a new project access permission entry.
    """
    access = ProjectAccess(**access.model_dump(), project_id=project.id)
    verify_access(session, access)
    session.add(access)
    session.commit()
    session.refresh(access)
    return access


@router.put("/{project_id}/access/{user_id}", response_model=ProjectAccessRead)
def update_project_access_permission(
    project: Annotated[UUID, Depends(get_project)],
    user: Annotated[UUID, Depends(get_user)],
    access: Annotated[ProjectAccessUpdate, Body(...)],
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.project_access_update.name])],
):
    """
    Updates a user's project access permissions.
    """

    access = ProjectAccess(**access.model_dump(), project_id=project.id, user_id=user.id)
    verify_access(session, access)
    result = session.query(ProjectAccess).filter_by(project_id=project.id, user_id=access.user_id).first()
    if not result:
        raise DataNotFoundError()
    for key, value in access.model_dump(exclude_unset=False).items():
        setattr(result, key, value)
    session.add(result)
    session.commit()
    session.refresh(result)
    return result
