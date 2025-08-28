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

import pytest
from datetime import datetime, date
from schema.project import ProjectState, ProjectType

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_set_completion_date_1(projects_fixture, project_type):
    """
    Projects with a state of not being completed should not have a completion date.
    """
    # Setup relevant data
    today = datetime.now().date()
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=project_type,
                                                 completion_date=today)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == project_type
    assert project.completion_date == today
    nested.commit()
    session.refresh(project)
    # Check results
    assert project.completion_date is None


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_set_completion_date_2(projects_fixture, project_type):
    """
    Projects with a state of completed should automatically receive a completion date.
    """
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.completed,
                                                 project_type=project_type,
                                                 completion_date=None)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.completed
    assert project.project_type == project_type
    assert project.completion_date is None
    nested.commit()
    session.refresh(project)
    # Check results
    assert project.completion_date == datetime.now().date()


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_set_completion_date_3(projects_fixture, project_type):
    """
    If the project status is updated to completed and a completion date is explicitly set, then this completion date
    must be used.
    """
    # Setup relevant data
    completion_date = date(2023, 10, 21)
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=project_type,
                                                 completion_date=None)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == project_type
    assert project.completion_date is None
    session.flush()
    # Change the project status to completed and explicitly set the completion date
    project.state = ProjectState.completed
    project.completion_date = completion_date
    session.add(project)
    session.flush()
    session.refresh(project)
    # Check results
    assert project.state == ProjectState.completed
    assert project.completion_date == completion_date


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_set_completion_date_3(projects_fixture, project_type):
    """
    If the project status is completed and the project completion date is explicitly set, then this completion date
    must be used.
    """
    # Setup relevant data
    completion_date = date(2023, 10, 21)
    today = datetime.now().date()
    session, nested, projects = projects_fixture(project_state=ProjectState.completed,
                                                 project_type=project_type,
                                                 completion_date=completion_date)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.completed
    assert project.project_type == project_type
    assert project.completion_date == completion_date
    session.flush()
    # Change the project status to completed and explicitly set the completion date
    project.completion_date = today
    session.add(project)
    session.flush()
    session.refresh(project)
    # Check results
    assert project.state == ProjectState.completed
    assert project.completion_date == today
