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
from schema.reporting.vulnerability.measure import MeasureResponse

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
# @pytest.mark.parametrize("user_name", [GuardianRoleEnum.admin.name])
def test_post_measure(
        measure_create_permission_fixture,
        get_measure_fixture,
        post_measure_fixture,
        delete_measure_fixture,
        user_name
):
    """
    Tests that an authenticated user can create a new measure.
    """
    # Check if the user has the required permission
    if measure_create_permission_fixture(user_name=user_name):
        report_language = get_measure_fixture()[0]
        response = post_measure_fixture(user_name=user_name, data=report_language)
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        result = MeasureResponse(**response_json)
        original = MeasureResponse(**report_language, id=result.id)
        assert result == original
        # Clean up
        delete_measure_fixture(user_name=GuardianRoleEnum.admin.name, measure_id=result.id) \
            .raise_for_status()
