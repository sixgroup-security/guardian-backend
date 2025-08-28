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
from schema.entity import ProviderRead, ProviderCreate

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("user_name", [item.name for item in GuardianRoleEnum])
# @pytest.mark.parametrize("user_name", [GuardianRoleEnum.admin.name])
def test_put_provider(
        provider_update_permission_fixture,
        get_provider_fixture,
        put_provider_fixture,
        post_provider_fixture,
        delete_provider_fixture,
        user_name
):
    """
    Tests that an authenticated user can update an existing provider.
    """
    # Check if the user has the required permission
    if provider_update_permission_fixture(user_name=user_name):
        # First, we create a provider
        provider = get_provider_fixture()
        response = post_provider_fixture(user_name=GuardianRoleEnum.admin.name, data=provider)
        assert response.status_code == status.HTTP_200_OK
        # Then, we update the provider
        result = ProviderRead(**response.json())
        provider["id"] = str(result.id)
        response = put_provider_fixture(user_name=user_name, data=provider)
        assert response.status_code == status.HTTP_200_OK
        result = ProviderRead(**response.json())
        original = ProviderCreate(**provider)
        assert result == original
        # Clean up
        delete_provider_fixture(user_name=GuardianRoleEnum.admin.name, customer_id=result.id) \
            .raise_for_status()
