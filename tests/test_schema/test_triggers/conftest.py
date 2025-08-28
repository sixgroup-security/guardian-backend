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

from ..conftest import *

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def applicationproject_fixture(applications_fixture, projects_fixture):
    """
    Fixture factory/closure that creates an application project mapping.
    """
    def _applicationproject_fixture(
            project_type=ProjectType.penetration_test,
            project_state=ProjectState.backlog,
            completion_date=None
    ):
        # Setup relevant data
        session, nested, projects = projects_fixture(
            project_type=project_type,
            project_state=project_state,
            completion_date=completion_date
        )
        _, _, applications = applications_fixture(
        )
        application = applications[0]
        project = projects[0]
        # Update database
        session.add(project)
        session.add(application)
        application.projects.append(project)
        session.flush()
        session.refresh(project)
        session.refresh(application)
        return session, nested, project, application
    yield _applicationproject_fixture
