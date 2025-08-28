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

import functools
from schema import engine
from datetime import datetime
from schema.entity import Entity
from schema.project import Project, ProjectType, ProjectState
from schema.project_user import ProjectAccess, ProjectTester
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

NOW = datetime.now().date()
TEST_PROJECT = Project(project_id="ID001",
                       name="Test Project",
                       state=ProjectState.backlog,
                       project_type=ProjectType.penetration_test,
                       start_date=datetime(2023, 9, 12).date(),
                       end_date=datetime(2023, 9, 17).date(),
                       created_at=NOW,
                       last_modified_at=NOW)
UPDATED_PROJECT = Project(project_id="ID002",
                          name="Updated Project",
                          state=ProjectState.running,
                          project_type=ProjectType.bug_bounty,
                          start_date=datetime(2023, 10, 12).date(),
                          end_date=datetime(2023, 10, 17).date(),
                          created_at=NOW,
                          last_modified_at=NOW)


def create_test_project() -> Project:
    """
    Creates or resets a test project in the database for testing purposes.
    """
    with Session(engine) as session:
        # Delete the project
        session.query(Entity).delete()
        session.query(ProjectAccess).delete()
        session.query(ProjectTester).delete()
        session.query(Project).filter_by(project_id=TEST_PROJECT.project_id).delete()
        session.commit()
        # Create the project with the initial values
        session.add(Project(**TEST_PROJECT.dict()))
        session.commit()
        tmp = session.query(Project).filter_by(project_id=TEST_PROJECT.project_id).one()
        result = Project(**tmp.dict())
        result.id = tmp.id
    return result


def delete_all_projects(function):
    """
    Decorator that deletes all projects before running the test.
    """
    @functools.wraps(function)
    def wrapper():
        with Session(engine) as session:
            session.query(Project).delete()
            session.commit()
        function()
    return wrapper