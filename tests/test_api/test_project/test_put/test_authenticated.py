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
from schema.project import ProjectCreate, ProjectRead
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
    Tests that an authenticated user can update an existing project.
    """
    # Check if the user has the required permission
    if project_update_permission_fixture(user_name=user_name):
        # First, we create an project
        project = get_project_fixture()
        response = post_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
        assert response.status_code == status.HTTP_200_OK
        result = ProjectRead(**response.json())
        # Then, we update the project
        project["id"] = str(result.id)
        response = put_project_fixture(user_name=user_name, data=project)
        assert response.status_code == status.HTTP_200_OK
        result = ProjectRead(**response.json())
        original = ProjectCreate(**project)
        assert result == original
        # Clean up
        delete_project_fixture(user_name=GuardianRoleEnum.admin.name, project_id=result.id) \
            .raise_for_status()


def test_testers_update(
    get_project_fixture,
    post_project_fixture,
    put_project_fixture,
    delete_project_fixture
):
    """
    Tests routers.project.Project.update_testers
    """
    # First, we create a project
    project = get_project_fixture(set_testers=True)
    assert len(project["testers"]) == 2
    response = post_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["testers"]) == 2
    # Test Case 1: Then, we remove all testers from the project
    tester_ids = [tester["id"] for tester in result["testers"]]
    project["id"] = result["id"]
    project["testers"] = [tester_ids[0]]
    response = put_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["testers"]) == 1
    # Clean up
    delete_project_fixture(user_name=GuardianRoleEnum.admin.name, project_id=project["id"]) \
        .raise_for_status()


def test_applications_update(
    get_project_fixture,
    post_project_fixture,
    put_project_fixture,
    delete_project_fixture
):
    """
    Tests routers.project.Project.update_applications
    """
    # First, we create a project
    project = get_project_fixture(set_applications=True)
    assert len(project["applications"]) == 2
    response = post_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["applications"]) == 2
    # Test Case 1: Then, we remove all testers from the project
    applications_ids = [tester["id"] for tester in result["applications"]]
    project["id"] = result["id"]
    project["applications"] = [applications_ids[0]]
    response = put_project_fixture(user_name=GuardianRoleEnum.admin.name, data=project)
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["applications"]) == 1
    # Clean up
    delete_project_fixture(user_name=GuardianRoleEnum.admin.name, project_id=project["id"]) \
        .raise_for_status()
