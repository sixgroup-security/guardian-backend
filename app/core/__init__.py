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

from fastapi import HTTPException, status
from schema.util import NotFoundError

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


class InvalidPlaybookStructure(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Playbook structure"
        )


class ExceptionWrapper(HTTPException):
    def __init__(self, exc: Exception):
        self.orig = exc
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


class DataNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__(message="")
