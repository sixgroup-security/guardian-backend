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

from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import API_PREFIX
from .auth import router as auth_router
from .reporting.report_version import router as report_version_router
from .reporting.file.report import router as report_file_router
from .reporting.file.report_template import router as report_template_file_router
from .reporting.file.test_procedure import router as test_procedure_file_router
from .reporting.file.vulnerability import router as vulnerability_file_router
from .reporting.file.report_procedure import router as report_procedure_file_router
from .reporting.vulnerability.rating import router as rating_router
from .reporting.vulnerability.vulnerability_template import router as vulnerability_template_router
from .reporting.vulnerability.test_procedure import router as test_procedure_router
from .reporting.report_section_management.vulnerability import router as vulnerability_router
from .reporting.report_section_management.report_section import router as report_section_router
from .reporting.report_section_management.report_procedure import router as report_procedure_router
from .reporting.report_section_management.report_section_playbook import router as report_section_playbook_router
from .reporting.vulnerability.playbook import router as playbook_router
from .reporting.report_template import router as report_template_router
from .reporting.vulnerability.measure import router as measure_router
from .reporting.pentest_report import router as pentest_report_router
from .reporting.report_language import router as report_language_router
from .tagging.bugcrowd_vrt import router as bugcrowd_vrt_router
from .tagging.mitre_cwe import router as mitre_cwe_router
from .entity import router as entity_router
from .project import router as project_router
from .user import router as user_router
from .tagging import router as tagging_router
from .application import router as application_router
from .project_access import router as project_user_router
from .project_comment import router as project_comment_router
from .country import router as country_router
from .websocket import router as websocket_router
from .status import router as status_router
from .reporting.report_scope import router as report_scope_router
from .access_token import router as access_token_router

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    """
    This middleware is used to add custom headers to the response.
    """
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        # response.headers['X-Content-Type-Options'] = 'nosniff'
        # response.headers['X-Frame-Options'] = 'DENY'
        # response.headers['Referrer-Policy'] = 'no-referrer'
        # response.headers['Content-Security-Policy'] = "default-src 'none';  frame-ancestors 'none'; require-trusted-types-for 'script'"
        # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        if request.url.path.startswith(API_PREFIX + "/countries/svg"):
            # Cache images for one day
            response.headers['Cache-Control'] = 'public, max-age=86400'
        else:
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Pragma'] = 'no-cache'
        return response


def add_routes(app):
    """
    This method can be used to add all routes to the given FastAPI app.
    :param app: FastAPI app
    """
    app.include_router(status_router)
    app.include_router(pentest_report_router)
    app.include_router(report_file_router)
    app.include_router(report_section_router)
    app.include_router(report_procedure_router)
    app.include_router(report_section_playbook_router)
    app.include_router(report_version_router)
    app.include_router(report_scope_router)
    app.include_router(country_router)
    app.include_router(report_language_router)
    app.include_router(vulnerability_template_router)
    app.include_router(vulnerability_router)
    app.include_router(test_procedure_router)
    app.include_router(rating_router)
    app.include_router(measure_router)
    app.include_router(playbook_router)
    app.include_router(report_template_router)
    app.include_router(report_template_file_router)
    app.include_router(test_procedure_file_router)
    app.include_router(vulnerability_file_router)
    app.include_router(report_procedure_file_router)
    app.include_router(auth_router)
    app.include_router(bugcrowd_vrt_router)
    app.include_router(mitre_cwe_router)
    app.include_router(tagging_router)
    app.include_router(application_router)
    app.include_router(user_router)
    app.include_router(entity_router)
    app.include_router(project_router)
    app.include_router(project_user_router)
    app.include_router(project_comment_router)
    app.include_router(websocket_router)
    app.include_router(access_token_router)
