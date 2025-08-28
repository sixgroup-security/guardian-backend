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
from datetime import datetime, timedelta
from core.auth import AuthenticationError
from schema.util import GuardianRoleEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_user_without_roles(create_test_user_fixture, db_session):
    """
    Users that do not have any roles assigned should not be able to log in.
    """
    session, _ = db_session
    with pytest.raises(AuthenticationError) as ex:
        create_test_user_fixture(session=session, roles=[])
        assert str(ex) == "401: You are not authorized to access this application."


def test_user_locked(create_test_user_fixture, db_session):
    """
    Users that are locked should not be able to log in.
    """
    session, _ = db_session
    with pytest.raises(AuthenticationError) as ex:
        create_test_user_fixture(session=session, roles=[GuardianRoleEnum.admin], locked=True)
        assert str(ex) == "401: You are not authorized to access this application."


def test_user_active_from(create_test_user_fixture, db_session):
    """
    Users that are not active yet should not be able to log in.
    """
    session, _ = db_session
    with pytest.raises(AuthenticationError) as ex:
        now = datetime.now()
        create_test_user_fixture(
            session=session,
            roles=[GuardianRoleEnum.admin],
            locked=False,
            active_from=now + timedelta(days=1)
        )
        assert str(ex) == "401: You are not authorized to access this application."


def test_user_active_until(create_test_user_fixture, db_session):
    """
    Users whose account validity has expired should not be able to log in.
    """
    session, _ = db_session
    with pytest.raises(AuthenticationError) as ex:
        now = datetime.now()
        create_test_user_fixture(
            session=session,
            roles=[GuardianRoleEnum.admin],
            locked=False,
            active_from=now - timedelta(days=2),
            active_until=now - timedelta(days=1)
        )
        assert str(ex) == "401: You are not authorized to access this application."
