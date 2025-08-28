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
from schema.user import UserRead, JsonWebToken, UserTest
from routers.user import API_USER_PREFIX

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_token_expiration():
    """
    Test if the token expiration is verified correctly.
    """
    response = client.get(
        API_USER_PREFIX + "/me",
        headers=UserTest.get_auth_header("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkB0ZXN0LmxvY2FsIiwic2NvcGVzIjpbInRlc3RfcHJvY2VkdXJlX2RlbGV0ZSIsImN1c3RvbWVyX2NyZWF0ZSIsImN1c3RvbWVyX3VwZGF0ZSIsImNhbGVuZGFyX3JlYWQiLCJhcHBsaWNhdGlvbl9jcmVhdGUiLCJ0ZXN0X3Byb2NlZHVyZV91cGRhdGUiLCJwcm9qZWN0X2FjY2Vzc19yZWFkIiwidnVsbmVyYWJpbGl0eV90ZW1wbGF0ZV91cGRhdGUiLCJhcHBsaWNhdGlvbl9yZWFkIiwicHJvamVjdF9kZWxldGUiLCJyZXBvcnRfbGFuZ3VhZ2VfcmVhZCIsInZ1bG5lcmFiaWxpdHlfdGVtcGxhdGVfdGFnX3JlYWQiLCJtZWFzdXJlX3JlYWQiLCJwcm9qZWN0X3JlYWQiLCJyZXBvcnRfdGVtcGxhdGVfY3JlYXRlIiwicmVwb3J0X3RlbXBsYXRlX3JlYWQiLCJhcHBsaWNhdGlvbl91cGRhdGUiLCJtZWFzdXJlX2NyZWF0ZSIsInVzZXJfbWVfcmVhZCIsInBlbnRlc3RfcGxheWJvb2tfZGVsZXRlIiwicHJvamVjdF90YWdfY3JlYXRlIiwicHJvamVjdF9hY2Nlc3NfdXBkYXRlIiwicmVwb3J0X3RlbXBsYXRlX3VwZGF0ZSIsImFwcGxpY2F0aW9uX2RlbGV0ZSIsInZ1bG5lcmFiaWxpdHlfdGVtcGxhdGVfY3JlYXRlIiwicGxheWJvb2tfZGVsZXRlIiwiYXBwbGljYXRpb25fdGFnX3JlYWQiLCJjdXN0b21lcl9kZWxldGUiLCJhcHBsaWNhdGlvbl9wcm9qZWN0X2JhdGNoX2NyZWF0ZSIsInVzZXJfY3JlYXRlIiwicHJvamVjdF90YWdfcmVhZCIsInVzZXJfZGVsZXRlIiwiY291bnRyeV9yZWFkIiwicGVudGVzdF9yZXBvcnRfcmVhZCIsInVzZXJfbWVfcmVwb3J0X2xhbmd1YWdlX3VwZGF0ZSIsImFwcGxpY2F0aW9uX3RhZ19jcmVhdGUiLCJ1c2VyX21lX3VwZGF0ZSIsInZ1bG5lcmFiaWxpdHlfdGVtcGxhdGVfcmVhZCIsInZ1bG5lcmFiaWxpdHlfdGVtcGxhdGVfdGFnX2NyZWF0ZSIsInByb2plY3RfYWNjZXNzX2RlbGV0ZSIsImFwcGxpY2F0aW9uX3Byb2plY3RfcmVhZCIsInBsYXlib29rX2NyZWF0ZSIsInVzZXJfdXBkYXRlIiwidGVzdF9wcm9jZWR1cmVfcmVhZCIsInJlcG9ydF9sYW5ndWFnZV9kZWxldGUiLCJwcm9qZWN0X2FjY2Vzc19jcmVhdGUiLCJwZW50ZXN0X3JlcG9ydF9jcmVhdGUiLCJtZWFzdXJlX3VwZGF0ZSIsInBlbnRlc3RfcmVwb3J0X3VwZGF0ZSIsInByb2plY3RfY3JlYXRlIiwicmVwb3J0X2xhbmd1YWdlX2NyZWF0ZSIsInByb3ZpZGVyX2NyZWF0ZSIsInRlc3RfcHJvY2VkdXJlX2NyZWF0ZSIsInByb3ZpZGVyX3VwZGF0ZSIsInBlbnRlc3RfcGxheWJvb2tfY3JlYXRlIiwicHJvdmlkZXJfcmVhZCIsInBlbnRlc3RfcGxheWJvb2tfdXBkYXRlIiwicmVwb3J0X3RlbXBsYXRlX2RlbGV0ZSIsInByb2plY3RfdXBkYXRlIiwicGxheWJvb2tfcmVhZCIsInJlcG9ydF9sYW5ndWFnZV91cGRhdGUiLCJwbGF5Ym9va191cGRhdGUiLCJjdXN0b21lcl9yZWFkIiwiZGFzaGJvYXJkX3JlYWQiLCJwZW50ZXN0X3JlcG9ydF9kZWxldGUiLCJ1c2VyX3JlYWQiLCJ2dWxuZXJhYmlsaXR5X3RlbXBsYXRlX2RlbGV0ZSIsInByb3ZpZGVyX2RlbGV0ZSIsInBlbnRlc3RfcGxheWJvb2tfcmVhZCIsIm1lYXN1cmVfZGVsZXRlIl0sImV4cCI6MTcyMjA5NDkwN30.mQ_GDYJJwQZC3t07MRuFAwu68osMIoqTBeB2cocue4Q")
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."


def test_invalid_signature(create_test_user_fixture, delete_user_fixture, db_session):
    """
    Test if the token expiration is verified correctly.
    """
    session, _ = db_session
    test_user = create_test_user_fixture(session=session, roles=[GuardianRoleEnum.admin])
    token = test_user.bearer
    # First, we try obtaining information about the user.
    response = client.get(API_USER_PREFIX + "/me", headers=test_user.get_authentication_header())
    assert response.status_code == status.HTTP_200_OK
    user = UserRead(**response.json())
    assert user.email == test_user.email
    # Next, we try to access the user with an empty token.
    response = client.get(API_USER_PREFIX + "/me", headers=test_user.get_empty_auth_header())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."
    # Next, we try to access the user with an invalid token.
    response = client.get(API_USER_PREFIX + "/me", headers=test_user.get_auth_header(token[:-1]))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."
    # We clean up the database.
    delete_user_fixture(session=session, user=test_user)
