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
from typing import Dict, Set, List
from fastapi import Response
from schema.util import ApiPermissionEnum
from schema.project import ProjectType
from schema.reporting.vulnerability.measure import Measure, MeasureCreate, MeasureUpdate, MeasureLanguage
from routers.reporting.vulnerability.measure import API_MEASURE_PREFIX
from schema.reporting.report_language import ReportLanguage
from test_api import TEST_USERS, client
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_measure_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new measure.
    """
    def _create_measure(
            name: str | None = None,
            project_types: Set[ProjectType] | None = None,
            recommendation: Dict[str, str] | None = None,
    ) -> List[Dict]:
        result = []
        for report_language in db_session[0].query(ReportLanguage).all():
            result.append({
                "name": name if name else str(uuid.uuid4()),
                "project_types": list(project_types) if project_types else [ProjectType.penetration_test.value],
                "recommendation": recommendation if recommendation else {report_language.language_code: str(uuid.uuid4())}
            })
        return result
    yield _create_measure


@pytest.fixture
def create_measure_fixture():
    """
    Fixture factory/closure that creates a new measure in the database.
    """
    def _create_measure(
            session: Session,
            name: str | None = None,
            project_types: Set[ProjectType] | None = None,
            recommendation: Dict[str, str] | None = None
    ) -> Measure:
        measure = Measure(
            name=name if name else str(uuid.uuid4()),
            project_types=project_types if project_types else {ProjectType.penetration_test},
        )
        if session.query(Measure).filter_by(name=measure.name).one_or_none():
            session.add(measure)
            if recommendation:
                for key, value in recommendation.items():
                    measure.multi_language_fields.append(MeasureLanguage(
                        language_id=session.query(ReportLanguage).filter_by(language_code=key).one().id,
                        recommendation=value
                    ))
            else:
                for report_language in session.query(ReportLanguage).all():
                    measure.multi_language_fields.append(MeasureLanguage(
                        language_id=report_language.id,
                        recommendation=str(uuid.uuid4())
                    ))
            session.commit()
            session.refresh(measure)
        return measure
    yield _create_measure


@pytest.fixture
def measure_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.measure_read])
    yield _permission_fixture


@pytest.fixture
def measure_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.measure_create])
    yield _permission_fixture


@pytest.fixture
def measure_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.measure_update])
    yield _permission_fixture


@pytest.fixture
def measure_delete_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.measure_delete])
    yield _permission_fixture


@pytest.fixture
def post_measure_fixture():
    """
    Fixture factory/closure that creates a new measure via the REST API.
    """
    def _post_measure_fixture(user_name: str | None, data: Dict) -> Response:
        measure = MeasureCreate.model_validate(data)
        payload = json.loads(measure.json(by_alias=True))
        response = client.post(
            API_MEASURE_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_measure_fixture


@pytest.fixture
def put_measure_fixture(db_session):
    """
    Fixture factory/closure that updates an existing measure via the REST API.
    """
    def _put_measure_fixture(user_name: str | None, data: Dict) -> Response:
        measure = MeasureUpdate(**data)
        payload = json.loads(measure.json(by_alias=True))
        response = client.put(
            API_MEASURE_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_measure_fixture


@pytest.fixture
def delete_measure_fixture():
    """
    Fixture factory/closure that deletes a measure via the REST API.
    """
    def _delete_measure_fixture(user_name: str | None, measure_id: uuid.UUID) -> Response:
        response = client.delete(
            API_MEASURE_PREFIX + f"/{measure_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_measure_fixture
