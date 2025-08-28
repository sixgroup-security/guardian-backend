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

import json
import uuid
import pytest
from typing import Dict
from datetime import date, datetime
from fastapi import Response
from schema import Country
from schema.util import GuardianRoleEnum, ApiPermissionEnum
from schema.project import (
    Project, ProjectCreate, ProjectUpdate, ProjectType, ProjectState, model_dump as project_model_dump
)
from test_api import TEST_USERS, client
from routers.project import API_PROJECT_PREFIX
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_project_fixture(
        create_user_fixture,
        create_application_fixture,
        create_customer_fixture,
        create_provider_fixture,
        db_session
):
    """
    Fixture factory/closure that provides a function to create a new project.
    """
    session, _ = db_session
    # Initialize database
    customer = create_customer_fixture(session=session)
    provider = create_provider_fixture(session=session)
    testers = [
        create_user_fixture(session=session, roles={GuardianRoleEnum.pentester}),
        create_user_fixture(session=session, roles={GuardianRoleEnum.pentester})
    ]
    applications = [
        create_application_fixture(session=session),
        create_application_fixture(session=session)
    ]
    location = session.query(Country).first()

    def get_create_project(
            name: str | None = None,
            project_type: ProjectType | None = None,
            year: int | None = None,
            state: ProjectState | None = None,
            start_date: date | None = None,
            end_date: date | None = None,
            completion_date: date | None = None,
            set_customer: bool = False,
            set_provider: bool = False,
            set_manager: bool = False,
            set_lead_tester: bool = False,
            set_testers: bool = False,
            set_applications: bool = False,
            comment: str = False,
    ) -> Dict:
        data = {
            "name": name if name else str(uuid.uuid4()),
            "project_type": project_type if project_type else ProjectType.penetration_test.value,
            "state": state if state else ProjectState.running.value,
            "year": year if year else datetime.now().year,
            "start_date": start_date if start_date else date.today(),
            "end_date": end_date,
            "completion_date": completion_date,
            "lead_tester_id": TEST_USERS[GuardianRoleEnum.pentester.name].id if set_lead_tester else None,
            "testers": [tester.id for tester in testers] if set_testers else None,
            "applications": [application.id for application in applications] if set_applications else None,
            "customer_id": customer.id if set_customer else None,
            "provider_id": provider.id if set_provider else None,
            "manager_id": TEST_USERS[GuardianRoleEnum.manager.name].id if set_manager else None,
            "location_id": location.id,
            "comment": comment if comment else "Comment"
        }
        return data
    yield get_create_project
    # Database cleanup
    session.delete(customer)
    session.delete(provider)
    for tester in testers:
        session.delete(tester)
    for application in applications:
        session.delete(application)
    session.commit()


@pytest.fixture
def create_project_fixture(get_project_fixture):
    """
    Fixture factory/closure that creates a new project in the database.
    """
    def _create_project(
            session: Session,
            **kwargs,
    ) -> Project:
        project_dict = get_project_fixture(**kwargs)
        project = ProjectCreate(**project_dict)
        project_json = project_model_dump(project)
        project = Project(**project_json)
        if not session.query(Project).filter_by(id=project.id).one_or_none():
            session.add(project)
            session.commit()
            session.refresh(project)
        return project
    yield _create_project


@pytest.fixture
def project_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.project_read])
    yield _permission_fixture


@pytest.fixture
def project_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.project_create])
    yield _permission_fixture


@pytest.fixture
def project_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.project_update])
    yield _permission_fixture


@pytest.fixture
def post_project_fixture(db_session):
    """
    Fixture factory/closure that creates a new project via the REST API.
    """
    def _post_project_fixture(user_name: str | None, data: Dict) -> Response:
        project = ProjectCreate(**data)
        payload = json.loads(project.json(by_alias=True))
        response = client.post(
            API_PROJECT_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_project_fixture


@pytest.fixture
def put_project_fixture(db_session):
    """
    Fixture factory/closure that updates an existing project via the REST API.
    """
    def _post_project_fixture(user_name: str | None, data: Dict) -> Response:
        project = ProjectUpdate(**data)
        payload = json.loads(project.json(by_alias=True))
        response = client.put(
            API_PROJECT_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_project_fixture


@pytest.fixture
def delete_project_fixture():
    """
    Fixture factory/closure that deletes an project via the REST API.
    """
    def _delete_project_fixture(user_name: str | None, project_id: uuid.UUID) -> Response:
        response = client.delete(
            API_PROJECT_PREFIX + f"/{project_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_project_fixture
