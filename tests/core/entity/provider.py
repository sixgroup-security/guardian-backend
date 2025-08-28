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
from schema.entity import Entity, EntityRoleEnum, ProviderCreate, ProviderUpdate
from schema.util import ApiPermissionEnum
from routers.entity import API_ENTITY_PREFIX, API_PROVIDER_SUFFIX
from test_api import TEST_USERS, client
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_provider_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new provider.
    """

    def _get_provider(
            name: str | None = None,
            abbreviation: str | None = None,
            address: str | None = None,
            location: uuid.UUID | None = None,
    ) -> Dict:
        country = db_session[0].query(Country).first()
        data = {
            "name": name if name else str(uuid.uuid4()),
            "location_id": location if location else country.id,
            "role": EntityRoleEnum.customer
        }
        if abbreviation:
            data["abbreviation"] = abbreviation
        if address:
            data["address"] = address
        return data

    yield _get_provider


@pytest.fixture
def create_provider_fixture(get_provider_fixture):
    """
    Fixture factory/closure that creates a new provider in the database.
    """
    def _create_provider(
            session: Session,
            **kwargs,
    ) -> Entity:
        # Create provider
        provider_dict = get_provider_fixture(**kwargs)
        provider = Entity(**provider_dict)
        if not session.query(Entity).filter_by(name=provider.name, role=EntityRoleEnum.provider).one_or_none():
            session.add(provider)
            session.commit()
            session.refresh(provider)
        return provider
    yield _create_provider


@pytest.fixture
def provider_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.provider_read])
    yield _permission_fixture


@pytest.fixture
def provider_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.provider_create])
    yield _permission_fixture


@pytest.fixture
def provider_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.provider_update])
    yield _permission_fixture


@pytest.fixture
def post_provider_fixture():
    """
    Fixture factory/closure that creates a new provider via the REST API.
    """
    def _post_provider_fixture(user_name: str | None, data: Dict) -> Response:
        provider = ProviderCreate.model_validate(data)
        payload = json.loads(provider.json(by_alias=True))
        response = client.post(
            API_ENTITY_PREFIX + API_PROVIDER_SUFFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_provider_fixture


@pytest.fixture
def put_provider_fixture():
    """
    Fixture factory/closure that updates an existing provider via the REST API.
    """
    def _put_provider_fixture(user_name: str | None, data: Dict) -> Response:
        provider = ProviderUpdate.model_validate(data)
        payload = json.loads(provider.json(by_alias=True))
        response = client.put(
            API_ENTITY_PREFIX + API_PROVIDER_SUFFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_provider_fixture


@pytest.fixture
def delete_provider_fixture():
    """
    Fixture factory/closure that deletes a provider via the REST API.
    """
    def _delete_provider_fixture(user_name: str | None, customer_id: uuid.UUID) -> Response:
        response = client.delete(
            API_ENTITY_PREFIX + API_PROVIDER_SUFFIX + f"/{customer_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_provider_fixture
