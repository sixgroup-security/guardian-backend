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

from test_api import init_test_users
from schema import engine, init_db
from tests.core.user import *
from tests.core.country import *
from tests.core.project import *
from tests.core.application import *
from tests.core.entity.customer import *
from tests.core.entity.provider import *
from tests.core.tagging.tagging import *
from tests.core.reporting.measure import *
from tests.core.reporting.report_language import *
from tests.core.reporting.report_template import *
from tests.core.reporting.file.file import *
from tests.core.reporting.pentest_report import *
from tests.core.reporting.vulnerability.playbook import *
from tests.core.reporting.vulnerability.rating import *
from tests.core.reporting.vulnerability.test_procedure import *
from tests.core.reporting.vulnerability.vulnerability_template import *

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture(scope='session', autouse=True)
def setup_user_in_db():
    init_db(drop_tables=True, create_tables=True, load_data=True)
    with Session(engine) as session:
        united_kingdom = session.query(Country).filter_by(code="GB").one()
        spain = session.query(Country).filter_by(code="ES").one()
        session.add(ReportLanguage(name="English", language_code="en", country=united_kingdom))
        session.add(ReportLanguage(name="Spanish", language_code="es", country=spain))
        session.commit()
    init_test_users()


@pytest.fixture
def db_session():
    """
    Fixture that creates a new database session and rolls back any changes after the test is complete.
    :return:
    """
    with Session(engine) as session:
        nested = session.begin_nested()
        yield session, nested
        # Perform database cleanup
        session.rollback()


@pytest.fixture
def projects_fixture(db_session):
    """
    Creates a project object ready to be inserted into the database.
    """
    def _projects_fixture(project_state=ProjectState.backlog,
                          project_type=ProjectType.penetration_test,
                          start_date=datetime.now(),
                          completion_date=None,
                          elements=1):
        """
        Fixture factory allowing for the creation of multiple projects.
        """
        session, nested = db_session
        location = session.query(Country).filter_by(code="CH").one()
        customer = Entity(name="Entity 1", role=EntityRoleEnum.customer, location=location)
        session.add(customer)
        projects = [Project(name=f"Project {i}",
                            project_type=project_type,
                            state=project_state,
                            start_date=start_date,
                            location=location,
                            completion_date=completion_date,
                            customer=customer) for i in range(elements)]
        return session, nested, projects
    yield _projects_fixture


@pytest.fixture
def applications_fixture(db_session):
    """
    Creates an application object ready to be inserted into the database.
    """

    def _applications_fixture(pentest_periodicity=None):
        session, nested = db_session
        applications = [Application(application_id=f"A-00{i}",
                                    name=f"App {i}",
                                    state=ApplicationState.production,
                                    pentest_periodicity=pentest_periodicity,
                                    description="App") for i in range(5)]
        return session, nested, applications
    yield _applications_fixture
