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
from schema.project import ProjectRead
from schema.util import GuardianRoleEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
#@pytest.mark.parametrize("user_name", [GuardianRoleEnum.admin.name])
def test_project(
    project_update_permission_fixture,
    get_project_fixture,
    post_project_fixture,
    put_project_fixture,
    delete_project_fixture,
    user_name
):
    """
    Tests that an unauthorized user can update an existing project.
    """
    # Check if the user has the required permission
    if not project_update_permission_fixture(user_name=user_name):
        # First, we create an project
        project = get_project_fixture()
        response = post_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
        assert response.status_code == status.HTTP_200_OK
        result = ProjectRead(**response.json())
        # Then, we update the project
        project["id"] = str(result.id)
        response = put_project_fixture(user_name=user_name, data=project)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.text == "401: Could not validate user."
        # Clean up
        delete_project_fixture(user_name=GuardianRoleEnum.admin.name, project_id=result.id) \
            .raise_for_status()
