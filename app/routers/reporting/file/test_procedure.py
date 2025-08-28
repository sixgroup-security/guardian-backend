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
from sqlalchemy import and_
from sqlalchemy.orm import Session
from schema import get_db
from schema.user import User
from schema.util import ApiPermissionEnum
from schema.reporting.vulnerability.test_procedure import TestProcedure
from schema.reporting.file import File, FileCreated, FileSourceEnum
from routers.user import get_current_active_user
from routers.reporting.file import add_file
from routers.reporting.vulnerability.test_procedure import API_TEST_PROCEDURE_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_FILE_SUFFIX = "/files"
API_TEMPLATE_FILE_PREFIX = API_TEST_PROCEDURE_PREFIX

router = APIRouter(
    prefix=API_TEMPLATE_FILE_PREFIX,
    tags=["test procedure"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.post("/{test_id}" + API_FILE_SUFFIX, response_model=FileCreated)
async def upload_files(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.test_procedure_update.name])],
    test_id: uuid.UUID,
    file: UploadFile = FastApiFile(...),
    session: Session = Depends(get_db)
):
    """
    Uploads a PNG file and assigns it to the given test procedure.
    """
    # TODO: Check whether the current user has permission to upload the file to the given report template.
    result = await add_file(session, file, FileSourceEnum.test_procedure)
    # We have to use the same session
    procedure = session.query(TestProcedure).filter_by(id=test_id).one()
    procedure.files.append(result)
    user = session.query(User).filter_by(id=current_user.id).one()
    user.files.append(result)
    session.commit()
    session.refresh(result)
    return result


@router.get("/{test_id}" + API_FILE_SUFFIX + "/{file_id}")
async def read_file(
    current_user: Annotated[User, Security(get_current_active_user,
                                           scopes=[ApiPermissionEnum.test_procedure_read.name])],
    file_id: uuid.UUID,
    test_id: uuid.UUID,
    response: Response,
    session: Session = Depends(get_db)
):
    """
    Returns a report file by its ID.
    """
    # TODO: Check whether the current user has permission to get the file from the given report template.
    file = session.query(File) \
        .join(TestProcedure, File.test_procedures) \
        .filter(and_(File.id == file_id,
                     File.source == FileSourceEnum.test_procedure,
                     TestProcedure.id == test_id)).one_or_none()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    response.headers["Content-Type"] = file.content_type
    return Response(content=file.content, media_type=file.content_type)
