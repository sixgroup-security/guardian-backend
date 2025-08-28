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
from schema.util import GuardianRoleEnum
from schema.entity import ProviderRead

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_put_provider(
        get_provider_fixture,
        put_provider_fixture,
        post_provider_fixture,
        delete_provider_fixture
):
    """
    Tests that an authenticated user can update an existing provider.
    """
    # First, we create a provider
    provider = get_provider_fixture()
    response = post_provider_fixture(user_name=GuardianRoleEnum.admin.name, data=provider)
    assert response.status_code == status.HTTP_200_OK
    # Then, we update the provider
    result = ProviderRead(**response.json())
    provider["id"] = str(result.id)
    response = put_provider_fixture(user_name=None, data=provider)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."
    # Clean up
    delete_provider_fixture(user_name=GuardianRoleEnum.admin.name, customer_id=result.id) \
        .raise_for_status()
