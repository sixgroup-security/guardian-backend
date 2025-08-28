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
# along with Guardian. If not, see <https://www.gnu.org/licenses/>.

import uuid
import json
import pytest
from typing import Dict
from fastapi import Response
from schema.util import ApiPermissionEnum
from schema.application import Application, ApplicationCreate, ApplicationState, ApplicationUpdate
from test_api import TEST_USERS, client
from routers.application import API_APPLICATION_PREFIX
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_application_fixture(create_customer_fixture, db_session):
    """
    Fixture factory/closure that provides a function to create a new application.
    """
    session, _ = db_session
    # Create entity
    owner = create_customer_fixture(name="owner", session=session)
    manager = create_customer_fixture(name="manager", session=session)

    def get_create_application(
            application_id: str | None = None,
            name: str | None = None,
            description: str | None = None,
            state: ApplicationState | None = None,
            owner_id: uuid.UUID | None = None,
            manager_id: uuid.UUID | None = None
    ) -> Dict:
        data = {
            "application_id": application_id if application_id else str(uuid.uuid4()),
            "name": name if name else str(uuid.uuid4()),
            "description": description if description else str(uuid.uuid4()),
            "state": state if state else ApplicationState.production.value,
            "owner_id": owner_id if owner_id else owner.id,
            "manager_id": manager_id if manager_id else manager.id
        }
        return data
    yield get_create_application
    # Delete entity
    session.delete(owner)
    session.delete(manager)
    session.commit()


@pytest.fixture
def create_application_fixture(get_application_fixture):
    """
    Fixture factory/closure that creates a new application in the database.
    """
    def _create_application(
            session: Session,
            **kwargs,
    ) -> Application:
        # Create customer
        application_dict = get_application_fixture(**kwargs)
        application = Application(**application_dict)
        if not session.query(Application).filter_by(application_id=application.application_id).one_or_none():
            session.add(application)
            session.commit()
            session.refresh(application)
        return application
    yield _create_application


@pytest.fixture
def application_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.application_read])
    yield _permission_fixture


@pytest.fixture
def application_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.application_create])
    yield _permission_fixture


@pytest.fixture
def application_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that updates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.application_update])
    yield _permission_fixture


@pytest.fixture
def post_application_fixture(db_session):
    """
    Fixture factory/closure that creates a new application via the REST API.
    """
    def _post_application_fixture(user_name: str | None, data: Dict) -> Response:
        application = ApplicationCreate(**data)
        payload = json.loads(application.json(by_alias=True))

        ApplicationCreate(**payload)
        response = client.post(
            API_APPLICATION_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_application_fixture


@pytest.fixture
def put_application_fixture(db_session):
    """
    Fixture factory/closure that updates an existing application via the REST API.
    """
    def _put_application_fixture(user_name: str | None, data: Dict) -> Response:
        application = ApplicationUpdate(**data)
        payload = json.loads(application.json(by_alias=True))
        response = client.put(
            API_APPLICATION_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_application_fixture


@pytest.fixture
def delete_application_fixture():
    """
    Fixture factory/closure that deletes an application via the REST API.
    """
    def _delete_application_fixture(user_name: str | None, application_id: uuid.UUID) -> Response:
        response = client.delete(
            API_APPLICATION_PREFIX + f"/{application_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_application_fixture
