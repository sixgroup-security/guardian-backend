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
from fastapi import UploadFile
from sqlalchemy.orm import Session
from routers.util import verify_png_image
from schema.reporting.file import File, FileCreate, FileSourceEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


async def add_file(session: Session, file: UploadFile, source: FileSourceEnum) -> File:
    """
    Add a file to the database.
    """
    image_data = await verify_png_image(file, max_file_size=1024 ** 2)
    # At the moment the File object cannot internally auto-compute the SHA256 value because it is not supported by
    # SQLModel and Pydantic
    file = FileCreate(
        content_type=file.content_type,
        file_name=file.filename,
        source=source,
        content=image_data
    )
    file = File(**file.model_dump())
    result = session.query(File).filter_by(sha256_value=file.sha256_value).one_or_none()
    if not result:
        result = file
        session.add(result)
    return result
