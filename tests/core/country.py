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
from schema.util import ApiPermissionEnum

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def country_read_permission_fixture(permission_fixture):
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str) -> bool:
        return permission_fixture(user_name, [ApiPermissionEnum.country_read])
    yield _permission_fixture
