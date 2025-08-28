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
from schema.util import GuardianRoleEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
# @pytest.mark.parametrize("user_name", [GuardianRoleEnum.admin.name])
def test_post_report_language(
        report_language_create_permission_fixture,
        get_report_language_fixture,
        post_report_language_fixture,
        user_name
):
    """
    Tests that an unauthorized user can create a new report language.
    """
    # Check if the user has the required permission
    if not report_language_create_permission_fixture(user_name=user_name):
        report_language = get_report_language_fixture()
        response = post_report_language_fixture(user_name=user_name, data=report_language)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.text == "401: Could not validate user."
