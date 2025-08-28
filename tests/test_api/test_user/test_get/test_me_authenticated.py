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
from schema.user import User
from schema.util import GuardianRoleEnum
from test_api import TEST_USERS, client
from routers.user import API_USER_PREFIX, UserReadMe

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
def test_user_me(
        user_me_read_permission_fixture,
        db_session,
        user_name
):
    """
    Tests that an authenticated user can get their own user information.
    """
    # Check if the user has the required permission
    if user_me_read_permission_fixture(user_name=user_name):
        session, _ = db_session
        response = client.get(API_USER_PREFIX + "/me", headers=TEST_USERS[user_name].get_authentication_header())
        assert response.status_code == status.HTTP_200_OK
        json_object = response.json()
        me = UserReadMe.model_construct(**json_object)
        # Obtain data from the database
        db_user = session.query(User).filter_by(id=me.id).one()
        assert "avatar" not in json_object
        assert json_object["selected_year"] == "All"
        assert db_user.email == me.email
        assert db_user.full_name == me.full_name
        assert "All" == me.selected_year
        assert me.light_mode is True
        assert json_object["full_name"] == TEST_USERS[user_name].full_name
        assert json_object["email"] == TEST_USERS[user_name].email
