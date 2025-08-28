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
from schema.project import Project, ProjectState, ProjectType

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.mark.parametrize("project_type", list(ProjectType))
@pytest.mark.parametrize("start_date", [date(2024, 10, 21),
                                        date(2023, 10, 22),
                                        date(2022, 10, 23)])
def test_insert_computing_project_year_increment_state_1(projects_fixture, project_type, start_date):
    """
    New projects should have their year and increment columns correctly computed.
    """
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=project_type,
                                                 start_date=start_date)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == project_type
    assert project.start_date == start_date
    nested.commit()
    session.refresh(project)
    # Check results
    assert project.increment == 1
    assert project.year == start_date.year


@pytest.mark.parametrize("new_project_type", list(ProjectType))
def test_update_computing_project_year_increment_state_1(projects_fixture, new_project_type):
    """
    Updated projects should have their year and increment columns correctly computed when the project type is updated.
    """
    today = datetime.now().date()
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=ProjectType.penetration_test,
                                                 start_date=today)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == ProjectType.penetration_test
    assert project.start_date == today
    nested.commit()
    # Update project
    project.project_type = new_project_type
    session.add(project)
    session.flush()
    session.refresh(project)
    assert project.increment == 1
    assert project.year == today.year


@pytest.mark.parametrize("start_date", [datetime.now().date(),
                                        date(2024, 10, 21),
                                        date(2023, 10, 22),
                                        date(2022, 10, 23)])
def test_update_computing_project_year_increment_state_2(projects_fixture, start_date):
    """
    CASE 1: Updated projects should have their year and increment columns correctly computed when the project start
    date is updated to another year.
    CASE 2: Updated projects should not have their year and increment columns updated when the project start date is
    is updated to the same year.
    """
    today = datetime.now().date()
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=ProjectType.penetration_test,
                                                 start_date=today)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == ProjectType.penetration_test
    assert project.start_date == today
    nested.commit()
    # Update project
    project.start_date = start_date
    session.add(project)
    session.flush()
    session.refresh(project)
    # Check results
    assert project.increment == 1
    assert project.year == start_date.year


@pytest.mark.parametrize("new_project_type", list(ProjectType))
@pytest.mark.parametrize("initial_start_date", [datetime.now().date(),
                                                date(2014, 10, 21),
                                                date(2013, 10, 22),
                                                date(2012, 10, 23)])
@pytest.mark.parametrize("new_start_date", [datetime.now().date(),
                                            date(2024, 10, 21),
                                            date(2023, 10, 22),
                                            date(2022, 10, 23)])
def test_insert_computing_project_year_increment_state_3(projects_fixture,
                                                         initial_start_date,
                                                         new_project_type,
                                                         new_start_date):
    """
    Updated projects should have their year and increment columns correctly computed.
    """
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=ProjectType.penetration_test,
                                                 start_date=initial_start_date)
    project = projects[0]
    # Update database
    session.add(project)
    assert project.state == ProjectState.backlog
    assert project.project_type == ProjectType.penetration_test
    assert project.start_date == initial_start_date
    nested.commit()
    project.project_type = new_project_type
    project.start_date = new_start_date
    session.flush()
    session.refresh(project)
    # Check results
    assert project.year == new_start_date.year
    assert project.increment == 1


@pytest.mark.parametrize("start_year", [2024, 2023])
def test_insert_computing_project_year_increment_state_4(projects_fixture, start_year):
    """
    New projects should have their year and increment columns correctly computed.
    """
    start_date = date(start_year, 10, 21)
    # Setup relevant data
    session, nested, projects = projects_fixture(project_state=ProjectState.backlog,
                                                 project_type=ProjectType.penetration_test,
                                                 start_date=start_date,
                                                 elements=5)
    assert len(projects) == 5
    # Update database
    for project in projects:
        session.add(project)
    nested.commit()
    # Check results
    results = session.query(Project).filter_by(year=start_year).order_by(Project.increment).all()
    for i in results:
        assert i.increment == results.index(i) + 1
        assert i.year == start_year
