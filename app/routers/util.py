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

import os
from enum import Enum
from typing import List
from sqlalchemy import extract, asc
from sqlalchemy.orm import Session
from schema.project import Project
from fastapi import UploadFile, File
from core.auth import UserUpdateError

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


class SupportedFileTypes(Enum):
    png = "png"
    xlsx = "xlsx"


FILE_SIGNATURES = {
    SupportedFileTypes.png.name: {
        "signature": b'\x89PNG\r\n\x1a\n',
        "extensions": [".png"],
        "mime_types": ["image/png"],
        "title": "PNG image"
    },
    SupportedFileTypes.xlsx.name: {
        "signature": b'PK\x03\x04',
        "extensions": [".xlsx"],
        "mime_types": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        "title": "Microsoft Excel file"
    }
}


def get_project_years(session: Session) -> List[str]:
    """
    This method returns a list of project years that are available in the database.
    """
    # TODO: Maybe we want to use the end_date instead of the start_date. In this case, we must make the end_date mandatory.
    result = [str(item[0]) for item in session.query(
        extract('year', Project.start_date).label('year')).distinct().order_by(asc('year')).all()]
    result.insert(0, "All")
    return result


async def _verify_file(expected_file: SupportedFileTypes,
                       file: UploadFile = File(...),
                       max_file_size: int = 5 * 1024 * 1024) -> bytes:
    """
    Ensures that the uploaded file is a valid PNG image.
    """
    message = f"Invalid file type. Only {FILE_SIGNATURES[expected_file.name]['title']}s are accepted."
    _, extension = os.path.splitext(file.filename)
    if ((extension or "").lower() not in FILE_SIGNATURES[expected_file.name]["extensions"] or
            file.content_type not in FILE_SIGNATURES[expected_file.name]["mime_types"]):
        raise UserUpdateError(message)
    # Read the image data
    image_data = await file.read()
    if len(image_data) > max_file_size:
        raise UserUpdateError("File size exceeds the limit.")
    # Check PNG signature (Magic Bytes)
    signature_length = len(FILE_SIGNATURES[expected_file.name]["signature"])
    if image_data[:signature_length] != FILE_SIGNATURES[expected_file.name]["signature"]:
        raise UserUpdateError(message)
    return image_data


async def verify_png_image(file: UploadFile = File(...), max_file_size: int = 5 * 1024 * 1024) -> bytes:
    """
    Ensures that the uploaded file is a valid PNG image.
    """
    return await _verify_file(SupportedFileTypes.png, file, max_file_size)


async def verify_xlsx_file(file: UploadFile = File(...), max_file_size: int = 5 * 1024 * 1024) -> bytes:
    """
    Ensures that the uploaded file is a valid PNG image.
    """
    return await _verify_file(SupportedFileTypes.xlsx, file, max_file_size)
