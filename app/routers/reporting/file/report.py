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

import uuid
import logging
from typing import Annotated
from fastapi import Response, Depends, APIRouter, Security, UploadFile, HTTPException, status, File as FastApiFile
from sqlalchemy.orm import Session
from schema import get_db
from schema.user import User
from schema.util import ApiPermissionEnum
from schema.reporting.file import FileCreated, FileSourceEnum
from routers.user import get_current_active_user
from routers.project import check_access_permission, get_project
from routers.reporting.file import add_file
from routers.reporting.report import API_REPORT_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_REPORT_FILE_PREFIX = API_REPORT_PREFIX + "/{report_id}/files"

router = APIRouter(
    prefix=API_REPORT_FILE_PREFIX,
    tags=["report template"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.post("", response_model=FileCreated)
async def upload_files(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.pentest_report_update.name])],
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    file: UploadFile = FastApiFile(...),
    session: Session = Depends(get_db)
):
    """
    Uploads a PNG files and assigns it to the given report.
    """
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    report = project.get_item(report_id=report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    result = await add_file(session, file, FileSourceEnum.report)
    report.files.append(result)
    user = session.query(User).filter_by(id=current_user.id).one()
    user.files.append(result)
    session.commit()
    session.refresh(result)
    return result


@router.get("/{file_id}")
async def read_file(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.pentest_report_read.name])],
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    file_id: uuid.UUID,
    response: Response,
    session: Session = Depends(get_db)
):
    """
    Returns a report file by its ID.
    """
    # TODO: Check whether the current user has permission to get the file from the given report template.
    project = get_project(project_id, session=session)
    check_access_permission(current_user, project)
    file = project.get_item(report_id=report_id, report_file_id=file_id)
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    response.headers["Content-Type"] = file.content_type
    return Response(content=file.content, media_type=file.content_type)
