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

import pytest
from fastapi import status
from schema.country import Country
from schema.util import GuardianRoleEnum
from test_api import TEST_USERS, client
from routers.country import API_COUNTRY_PREFIX, API_COUNTRY_FLAG_SUFFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
def test_country(country_read_permission_fixture, user_name):
    """
    Tests that an authenticated user can get a list of countries.
    """
    # Check if the user has the required permission
    if country_read_permission_fixture(user_name=user_name):
        response = client.get(API_COUNTRY_PREFIX, headers=TEST_USERS[user_name].get_authentication_header())
        assert response.status_code == status.HTTP_200_OK
        results = response.json()
        assert len(results) > 0
        json_object = response.json()[0]
        assert len(json_object) == 3
        assert json_object["name"] == "Spain"
        assert json_object["country_code"] == "ES"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
def test_country_flag(country_read_permission_fixture, db_session, user_name):
    """
    Tests that an authenticated user can get the SVG of an existing country.
    """
    if country_read_permission_fixture(user_name=user_name):
        session, _ = db_session
        country = session.query(Country).filter_by(code="AF").one()
        response = client.get((API_COUNTRY_PREFIX + API_COUNTRY_FLAG_SUFFIX).format(country_code=country.code),
                              headers=TEST_USERS[user_name].get_authentication_header())
        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode("utf-8") == country.svg_image


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
def test_country_flag_not_found(country_read_permission_fixture, user_name):
    """
    Tests that an authenticated user tries to get the SVG of a non-existing country.
    """
    if country_read_permission_fixture(user_name=user_name):
        response = client.get((API_COUNTRY_PREFIX + API_COUNTRY_FLAG_SUFFIX).format(country_code="INVALID_CODE"),
                              headers=TEST_USERS[user_name].get_authentication_header())
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.content == b'404: Country not found'
