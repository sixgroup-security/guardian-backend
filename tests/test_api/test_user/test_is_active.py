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

from datetime import date, timedelta
from test_api import TEST_EMAIL
from schema.user import User

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_active():
    """
    User should be active, if locked attribute is set to False and active_from is set to a date in the past.
    """
    user = User(email=TEST_EMAIL, roles=[], locked=False, active_from=date.today(), active_until=None)
    assert user.is_active is True


def test_locked_true():
    """
    User should be inactive, if locked attribute is set to True and active_from is set to a date in the past.
    :return:
    """
    user = User(email=TEST_EMAIL, roles=[], locked=True, active_from=date.today(), active_until=None)
    assert user.is_active is False


def test_account_expired():
    """
    User should be inactive, if locked attribute is set to False, active_from is set to a date in the past and
    active_until is set to a date in the past.
    :return:
    """
    user = User(
        email=TEST_EMAIL,
        roles=[],
        locked=False,
        active_from=date.today(),
        active_until=date(2020, 1, 1)
    )
    assert user.is_active is False


def test_account_not_yet_active():
    """
    User should be inactive, if locked attribute is set to False and active_from is set to a date in the future.
    """
    user = User(
        email=TEST_EMAIL,
        roles=[],
        locked=False,
        active_from=date.today() + timedelta(3600),
        active_until=None
    )
    assert user.is_active is False
