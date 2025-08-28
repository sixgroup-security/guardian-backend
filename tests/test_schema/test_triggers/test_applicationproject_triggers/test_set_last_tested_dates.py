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

import pytest
from datetime import datetime
from schema.project import ProjectState, ProjectType
from dateutil.relativedelta import relativedelta

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_insert_set_last_date_1(applicationproject_fixture, project_type):
    """
    Test the trigger's INSERT section.

    The database trigger should not set the last_pentest date if the project is not completed.
    """
    session, nested, project, application = applicationproject_fixture(project_state=ProjectState.backlog,
                                                                       project_type=project_type,
                                                                       completion_date=None)
    # Check results
    assert project.completion_date is None
    assert application.last_pentest is None
    assert application.next_pentest is None
    assert application.project_count == 1
    return project, application


@pytest.mark.parametrize("project_type", list(ProjectType))
@pytest.mark.parametrize("pentest_periodicity", [None, 24])
def test_insert_set_last_date_2(applications_fixture,
                                projects_fixture,
                                project_type,
                                pentest_periodicity):
    """
    Test the trigger's INSERT section.

    The database trigger should set the last_pentest date if an application is added to a project that is completed.
    """
    session, nested, projects = projects_fixture(project_state=ProjectState.completed,
                                                 project_type=project_type)
    _, _, applications = applications_fixture(pentest_periodicity=pentest_periodicity)
    application = applications[0]
    project = projects[0]
    # Update database
    session.add(project)
    session.add(application)
    application.projects.append(project)
    nested.commit()
    session.refresh(project)
    session.refresh(application)
    # Check results
    assert application.project_count == 1
    assert project.completion_date == datetime.now().date()
    if project_type == ProjectType.penetration_test:
        assert application.last_pentest == project.completion_date
        assert application.next_pentest == (project.completion_date +
                                            relativedelta(months=pentest_periodicity) if pentest_periodicity else None)
    else:
        assert application.last_pentest is None


@pytest.mark.parametrize("project_type", list(ProjectType))
@pytest.mark.parametrize("pentest_periodicity", [None, 24])
def test_delete_set_last_date_1(applicationproject_fixture,
                                project_type,
                                pentest_periodicity):
    """
    Test the trigger's DELETE section.

    The database trigger should set the last_pentest date back to NULL, if the application is removed from its only
    completed pentest project.
    """
    today = datetime.now().date()
    session, nested, project, application = applicationproject_fixture(
        project_state=ProjectState.completed,
        project_type=project_type,
        pentest_periodicity=pentest_periodicity,
        completion_date=None
    )
    # Check results
    assert application.project_count == 1
    assert project.project_type == project_type
    assert project.state == ProjectState.completed
    assert project.completion_date == today
    if project_type == ProjectType.penetration_test:
        assert application.last_pentest == today
        assert application.next_pentest == (project.completion_date +
                                            relativedelta(months=pentest_periodicity) if pentest_periodicity else None)
    else:
        assert application.last_pentest is None
    # Update the database
    session.delete(project.application_project_links[0])
    session.flush()
    session.refresh(project)
    session.refresh(application)
    # Check results
    assert project.completion_date == today
    # Check pentests
    assert application.last_pentest is None
    assert application.pentest_periodicity == pentest_periodicity
    assert application.next_pentest is None
