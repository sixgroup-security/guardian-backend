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

from fastapi import status
from test_api import client
from schema.country import Country
from routers.country import API_COUNTRY_PREFIX, API_COUNTRY_FLAG_SUFFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_country():
    """
    Tests that an unauthenticated user cannot get a list of countries.
    """
    response = client.get(API_COUNTRY_PREFIX)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.content == b"401: Could not validate user."


def test_country_flag(db_session):
    """
    Tests that an unauthenticated user cannot get the SVG of an existing country.
    """
    session, _ = db_session
    country = session.query(Country).filter_by(code="AF").one()
    response = client.get((API_COUNTRY_PREFIX + API_COUNTRY_FLAG_SUFFIX).format(country_code=country.code))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.content == b"401: Could not validate user."


def test_country_flag_not_found():
    """
    Tests that an unauthenticated user cannot get the SVG of a non-existing country.
    """
    response = client.get((API_COUNTRY_PREFIX + API_COUNTRY_FLAG_SUFFIX).format(country_code="INVALID_CODE"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.content == b"401: Could not validate user."
