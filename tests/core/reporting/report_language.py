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
from schema.util import ApiPermissionEnum
from schema.reporting.report_language import ReportLanguage, ReportLanguageCreate, ReportLanguageUpdate
from routers.reporting.report_language import API_REPORT_LANGUAGE_PREFIX
from test_api import TEST_USERS, client
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_report_language_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new report language.
    """
    def _get_report_language(
            name: str | None = None,
            language_code: str | None = None,
            is_default: bool = False,
            country_id: uuid.UUID | None = None,
    ) -> Dict:
        country = db_session[0].query(Country).first()
        data = {
            "name": name if name else str(uuid.uuid4()),
            "language_code": language_code if language_code else str(uuid.uuid4()),
            "is_default": is_default,
            "country_id": country_id if country_id else country.id
        }
        return data
    yield _get_report_language


@pytest.fixture
def create_report_language_fixture(get_report_language_fixture):
    """
    Fixture factory/closure that creates a new report language in the database.
    """
    def _create_report_language(
            session: Session,
            **kwargs,
    ) -> ReportLanguage:
        report_language_dict = get_report_language_fixture(**kwargs)
        report_language = ReportLanguage(**report_language_dict)
        if not session.query(ReportLanguage).filter_by(language_code=report_language.language_code).one_or_none():
            session.add(report_language)
            session.commit()
            session.refresh(report_language)
        return report_language
    yield _create_report_language


@pytest.fixture
def report_language_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_language_read])
    yield _permission_fixture


@pytest.fixture
def report_language_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_language_create])
    yield _permission_fixture


@pytest.fixture
def report_language_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_language_update])
    yield _permission_fixture


@pytest.fixture
def report_language_delete_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_language_delete])
    yield _permission_fixture


@pytest.fixture
def post_report_language_fixture():
    """
    Fixture factory/closure that creates a new report language via the REST API.
    """
    def _post_report_language_fixture(user_name: str | None, data: Dict) -> Response:
        report_language = ReportLanguageCreate.model_validate(data)
        payload = json.loads(report_language.json(by_alias=True))
        response = client.post(
            API_REPORT_LANGUAGE_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_report_language_fixture


@pytest.fixture
def put_report_language_fixture(db_session):
    """
    Fixture factory/closure that updates an existing report language via the REST API.
    """
    def _put_report_language_fixture(user_name: str | None, data: Dict) -> Response:
        report_language = ReportLanguageUpdate(**data)
        payload = json.loads(report_language.json(by_alias=True))
        response = client.put(
            API_REPORT_LANGUAGE_PREFIX,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_report_language_fixture


@pytest.fixture
def delete_report_language_fixture():
    """
    Fixture factory/closure that deletes a report language via the REST API.
    """
    def _delete_report_language_fixture(user_name: str | None, report_language_id: uuid.UUID) -> Response:
        response = client.delete(
            API_REPORT_LANGUAGE_PREFIX + f"/{report_language_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_report_language_fixture
