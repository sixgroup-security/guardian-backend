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
from typing import Annotated, List
from fastapi import Response, HTTPException, Depends, Security, APIRouter
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from schema import get_db
from schema.user import User
from schema.util import ApiPermissionEnum
from schema.country import Country, CountryLookup
from routers.user import get_current_active_user
from core.config import API_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

API_COUNTRY_SUFFIX = "/countries"
API_COUNTRY_FLAG_SUFFIX = "/svg/{country_code}"
API_COUNTRY_PREFIX = API_PREFIX + API_COUNTRY_SUFFIX


router = APIRouter(
    prefix=API_COUNTRY_PREFIX,
    tags=["country"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("", response_model=List[CountryLookup])
def read_countries(
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.country_read.name])],
    session: Session = Depends(get_db)
):
    """
    Returns all country information.
    """
    return session.query(Country).order_by(desc(Country.default), asc(Country.name)).all()


@router.get(API_COUNTRY_FLAG_SUFFIX)
async def read_country_flag(
    country_code: str,
    current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.country_read.name])],
    session: Session = Depends(get_db)
):
    """
    Returns flag by its country code.
    """
    country = session.query(Country).filter_by(code=country_code.upper()).one_or_none()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    return Response(content=country.svg_image, media_type="image/svg+xml")
