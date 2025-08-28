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
from typing import Annotated
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from schema import get_db
from schema.util import ApiPermissionEnum, get_by_id, update_attributes, StatusEnum, StatusMessage
from schema.project import Project
from schema.project_comment import ProjectCommentUpdate
from routers.user import get_current_active_user, User
from .project import API_PROJECT_PREFIX, check_access_permission

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_PROJECT_COMMENT_PREFIX = API_PROJECT_PREFIX + "/{project_id}/comments"


router = APIRouter(
    prefix=API_PROJECT_COMMENT_PREFIX,
    tags=["project"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


#@router.delete("/{comment_id}", response_model=StatusMessage)
#def delete_project_comment(
#    current_user: Annotated[User, Security(
#        get_current_active_user,
#        scopes=[ApiPermissionEnum.project_comment_delete.name]
#    )],
#    project_id: UUID,
#    comment_id: UUID,
#    session: Session = Depends(get_db)
#):
#    """
#    Deletes a project comment by its ID.
#
#    Users can only delete their own comments.
#    """
#    project = get_by_id(session, Project, project_id)
#    check_access_permission(current_user, project)
#    comment = project.get_item(comment_id=comment_id)
#    if comment and comment.user_id == current_user.id:
#        session.delete(comment)
#        session.commit()
#    return StatusMessage(
#        status=status.HTTP_200_OK,
#        severity=StatusEnum.success,
#        message=f"Comment successfully deleted."
#    )


@router.put("", response_model=StatusMessage)
def update_project_comment(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.project_update.name])],
    project_id: UUID,
    comment: Annotated[ProjectCommentUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a project comment by its ID.

    Users can only update their own comments.
    """
    project = get_by_id(session, Project, project_id)
    check_access_permission(current_user, project)
    result = project.get_item(comment_id=comment.id)
    if result and result.user_id == current_user.id:
        update_attributes(
            target=result,
            source=comment,
            source_model=ProjectCommentUpdate,
            exclude_unset=False
        )
        session.add(result)
        session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Comment successfully updated."
    )
