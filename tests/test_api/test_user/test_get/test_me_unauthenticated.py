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
from routers.user import API_USER_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_user_me(
        user_me_read_permission_fixture,
        db_session
):
    """
    Tests that an unauthenticated user can get their own user information.
    """
    # Check if the user has the required permission
    session, _ = db_session
    response = client.get(API_USER_PREFIX + "/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."
