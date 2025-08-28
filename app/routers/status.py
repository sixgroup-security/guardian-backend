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

import logging
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from schema import get_db
from schema.country import Country
from core.config import API_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_STATUS_SUFFIX = "/status"
API_STATUS_PREFIX = API_PREFIX + API_STATUS_SUFFIX


router = APIRouter(
    prefix=API_STATUS_PREFIX,
    tags=["country"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("")
def read_countries(
    session: Session = Depends(get_db)
):
    """
    Returns all country information.
    """
    _ = session.query(Country).count()
    return {"status": "ok"}
