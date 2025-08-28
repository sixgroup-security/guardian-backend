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

import io
import uuid
import pytest
from typing import ByteString
from test_api import TEST_USERS, client

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture()
def upload_png_fixture():
    """
    This fixture uploads a PNG file.
    """
    def _upload_png(
            api_path: str,
            user_name: str = None,
            file_name: str = None,
            mime_type: str = None,
            content: ByteString = None
    ):
        name = file_name if file_name else f"{uuid.uuid4()}.png"
        file_content = (io.BytesIO(content) if content else (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00d' + uuid.uuid4().bytes))
        files = {"file": (name, file_content, mime_type if mime_type else "image/png")}
        response = client.post(
            api_path,
            headers=TEST_USERS[user_name].get_authentication_header() if user_name else None,
            files=files
        )
        return response
    yield _upload_png
