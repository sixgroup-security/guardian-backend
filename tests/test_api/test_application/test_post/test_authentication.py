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
from schema.application import ApplicationCreate, ApplicationRead
from schema.util import GuardianRoleEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
def test_application(
        application_create_permission_fixture,
        get_application_fixture,
        post_application_fixture,
        delete_application_fixture,
        user_name
):
    """
    Tests that an authenticated user can create a new application.
    """
    # Check if the user has the required permission
    if application_create_permission_fixture(user_name=user_name):
        application = get_application_fixture()
        response = post_application_fixture(user_name=user_name, data=application)
        assert response.status_code == status.HTTP_200_OK
        result = ApplicationRead(**response.json())
        original = ApplicationCreate(**application)
        assert result == original
        # Clean up
        delete_application_fixture(user_name=GuardianRoleEnum.admin.name, application_id=result.id) \
            .raise_for_status()
