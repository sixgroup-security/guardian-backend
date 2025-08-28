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

from ..conftest import *
from typing import List
from schema.util import ApiPermissionEnum, ROLE_PERMISSION_MAPPING

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def permission_fixture():
    """
    Fixture factory/closure that creates a permission.
    """
    def _permission_fixture(user_name: str, scopes: List[ApiPermissionEnum]) -> bool:
        result = []
        for scope in scopes:
            result.append(scope.name in ROLE_PERMISSION_MAPPING[user_name])
        return any(result)
    yield _permission_fixture
