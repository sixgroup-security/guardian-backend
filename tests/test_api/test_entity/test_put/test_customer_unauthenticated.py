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
from schema.entity import CustomerRead

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_put_customer(
        get_customer_fixture,
        put_customer_fixture,
        post_customer_fixture,
        delete_customer_fixture
):
    """
    Tests that an unauthenticated user can update an existing customer.
    """
    # First, we create a customer
    customer = get_customer_fixture()
    response = post_customer_fixture(user_name=GuardianRoleEnum.admin.name, data=customer)
    assert response.status_code == status.HTTP_200_OK
    # Then, we update the customer
    result = CustomerRead(**response.json())
    customer["id"] = str(result.id)
    response = put_customer_fixture(user_name=None, data=customer)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "401: Could not validate user."
    # Clean up
    delete_customer_fixture(user_name=GuardianRoleEnum.admin.name, customer_id=result.id) \
        .raise_for_status()
