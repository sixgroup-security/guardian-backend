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
from typing import Dict, List
from fastapi import Response, status
from schema.util import ApiPermissionEnum, GuardianRoleEnum
from schema.project import ProjectType
from schema.reporting.report_template import (
    ReportTemplate, ReportTemplateCreate, ReportTemplateUpdate, ReportTemplateFileVersion
)
from routers.reporting.report_template import API_TEMPLATE_PREFIX
from routers.reporting.file.report_template import API_FILE_SUFFIX
from schema.reporting.report_language import ReportLanguage
from test_api import TEST_USERS, client
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_report_template_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new report template.
    """
    def _create_report_template(
            name: str | None = None,
            project_type: ProjectType | None = None,
            executive_summary: Dict[str, str] | None = None,
            prefix_section_text: Dict[str, str] | None = None,
            postfix_section_text: Dict[str, str] | None = None,
            summary_template: Dict[str, str] | None = None
    ) -> List[Dict]:
        result = []
        for report_language in db_session[0].query(ReportLanguage).all():
            result.append({
                "name": name if name else str(uuid.uuid4()),
                "version": ReportTemplateFileVersion.v1.value,
                "project_type": project_type if project_type else ProjectType.penetration_test.value,
                "executive_summary": executive_summary if executive_summary else {report_language.language_code: str(uuid.uuid4())},
                "prefix_section_text": prefix_section_text if prefix_section_text else {report_language.language_code: str(uuid.uuid4())},
                "postfix_section_text": postfix_section_text if postfix_section_text else {report_language.language_code: str(uuid.uuid4())},
                "summary_template": summary_template if summary_template else {report_language.language_code: str(uuid.uuid4())}
            })
        return result
    yield _create_report_template


@pytest.fixture
def create_report_template_fixture(get_report_template_fixture, post_report_template_fixture):
    """
    Fixture factory/closure that creates a new report template in the database.
    """
    def _create_report_template(
            session: Session,
            **kwargs
    ) -> ReportTemplate:
        report_template_dict = get_report_template_fixture(**kwargs)
        response = post_report_template_fixture(
            user_name=GuardianRoleEnum.admin.name,
            data=report_template_dict[0]
        )
        assert response.status_code == status.HTTP_200_OK
        report_template = session.query(ReportTemplate).filter_by(id=response.json()["id"]).one()
        return report_template
    yield _create_report_template


@pytest.fixture
def report_template_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_template_read])
    yield _permission_fixture


@pytest.fixture
def report_template_create_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_template_create])
    yield _permission_fixture


@pytest.fixture
def report_template_update_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_template_update])
    yield _permission_fixture


@pytest.fixture
def report_template_delete_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.report_template_delete])
    yield _permission_fixture


@pytest.fixture
def post_report_template_fixture():
    """
    Fixture factory/closure that creates a new report template via the REST API.
    """
    def _post_report_template_fixture(user_name: str | None, data: Dict) -> Response:
        report_template = ReportTemplateCreate.model_validate(data)
        payload = json.loads(report_template.json(by_alias=True))
        response = client.post(
            API_TEMPLATE_PREFIX + "/pentest",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _post_report_template_fixture


@pytest.fixture
def put_report_template_fixture(db_session):
    """
    Fixture factory/closure that updates an existing report template via the REST API.
    """
    def _put_report_template_fixture(user_name: str | None, data: Dict) -> Response:
        report_template = ReportTemplateUpdate(**data)
        payload = json.loads(report_template.json(by_alias=True))
        response = client.put(
            API_TEMPLATE_PREFIX + "/pentest",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            json=payload
        )
        return response
    yield _put_report_template_fixture


@pytest.fixture
def delete_report_template_fixture():
    """
    Fixture factory/closure that deletes a report template via the REST API.
    """
    def _delete_report_template_fixture(user_name: str | None, report_template_id: uuid.UUID) -> Response:
        response = client.delete(
            API_TEMPLATE_PREFIX + f"/pentest/{report_template_id}",
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None
        )
        return response
    yield _delete_report_template_fixture


@pytest.fixture
def post_report_template_file_fixture(
        upload_png_fixture
):
    """
    Fixture factory/closure that uploads a new report template file via the REST API.
    """
    def _post_report_template_file_fixture(
            report_template_id: uuid.UUID,
            user_name: str | None,
            **kwargs
    ) -> Response:
        return upload_png_fixture(
            api_path=API_TEMPLATE_PREFIX + f"/{report_template_id}" + API_FILE_SUFFIX,
            user_name=user_name,
            **kwargs,
        )
    yield _post_report_template_file_fixture
