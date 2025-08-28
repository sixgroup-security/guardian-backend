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

from test_api import client
from fastapi import status
from schema.util import GuardianRoleEnum
from schema.user import UserRead, JsonWebToken
from routers.user import API_USER_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_token_revoked(create_test_user_fixture, delete_user_fixture, db_session):
    """
    If a user logs out, then he should not be able to use the session token anymore.
    """
    session, _ = db_session
    test_user = create_test_user_fixture(session=session, roles=[GuardianRoleEnum.admin])
    # First, we try obtaining information about the user.
    response = client.get(API_USER_PREFIX + "/me", headers=test_user.get_authentication_header())
    assert response.status_code == status.HTTP_200_OK
    user = UserRead(**response.json())
    assert user.email == test_user.email
    # Next, we log out the user.
    response = client.get("/api/logout", headers=test_user.get_authentication_header(), follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert session.query(JsonWebToken).filter_by(user_id=test_user.id).one().revoked is True
    # Finally, we try obtaining information about the user again.
    response = client.get(API_USER_PREFIX + "/me", headers=test_user.get_authentication_header())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    logout_content = response.content
    assert b'401: Token has been revoked. Please login again.' == response.content
    # We clean up the database.
    delete_user_fixture(session=session, user=test_user)
