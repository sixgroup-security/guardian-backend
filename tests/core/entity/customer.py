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

import uuid
import json
import pytest
from typing import Dict
from fastapi import Response
from schema import Country
from schema.entity import Entity, EntityRoleEnum, CustomerCreate, CustomerUpdate
from schema.util import GuardianRoleEnum, ApiPermissionEnum
from routers.entity import API_ENTITY_PREFIX, API_CUSTOMER_SUFFIX
from test_api import TEST_USERS, client
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_customer_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new customer.
    """
    def _get_customer(
            name: str | None = None,
            abbreviation: str | None = None,
            address: str | None = None,
            manager: uuid.UUID | None = None,
            location: uuid.UUID | None = None,
    ) -> Dict:
        country = db_session[0].query(Country).first()
        data = {
            "name": name if name else str(uuid.uuid4()),
            "location_id": location if location else country.id,
            "manager_id": manager if manager else TEST_USERS[GuardianRoleEnum.manager.name].id,
            "role": EntityRoleEnum.customer
        }
        if abbreviation:
            data["abbreviation"] = abbreviation
        if address:
            data["address"] = address
        return data

    yield _get_customer


@pytest.fixture
def create_customer_fixture(get_customer_fixture):
    """
    Fixture factory/closure that creates a new customer in the database.
    """
    def _create_customer(
            session: Session,
            **kwargs,
    ) -> Entity:
        # Create customer
        customer_dict = get_customer_fixture(**kwargs)
        customer = Entity(**customer_dict)
        if not session.query(Entity).filter_by(name=customer.name, role=EntityRoleEnum.customer).one_or_none():
            session.add(customer)
            session.commit()
            session.refresh(customer)
        return customer
    yield _create_customer


@pytest.fixture
def customer_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.customer_read])
    yield _permission_fixture


@pytest.fixture
def customer_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.customer_create])
    yield _permission_fixture


@pytest.fixture
def customer_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.customer_update])
    yield _permission_fixture


@pytest.fixture
def post_customer_fixture():
    """
    Fixture factory/closure that creates a new customer via the REST API.
    """
    def _post_customer_fixture(user_name: str | None, data: Dict) -> Response:
        customer = CustomerCreate.model_validate(data)
        payload = json.loads(customer.json(by_alias=True))
        response = client.post(
            API_ENTITY_PREFIX + API_CUSTOMER_SUFFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_customer_fixture


@pytest.fixture
def put_customer_fixture(db_session):
    """
    Fixture factory/closure that updates an existing customer via the REST API.
    """
    def _put_customer_fixture(user_name: str | None, data: Dict) -> Response:
        application = CustomerUpdate(**data)
        payload = json.loads(application.json(by_alias=True))
        response = client.put(
            API_ENTITY_PREFIX + API_CUSTOMER_SUFFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_customer_fixture


@pytest.fixture
def delete_customer_fixture():
    """
    Fixture factory/closure that deletes a customer via the REST API.
    """
    def _delete_customer_fixture(user_name: str | None, customer_id: uuid.UUID) -> Response:
        response = client.delete(
            API_ENTITY_PREFIX + API_CUSTOMER_SUFFIX + f"/{customer_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_customer_fixture
