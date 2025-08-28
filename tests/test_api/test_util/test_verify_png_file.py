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
import asyncio
from routers.util import verify_png_image
from starlette.datastructures import UploadFile, Headers
from routers.util import UserUpdateError

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_invalid_file_type():
    """
    Test the verify_png_image method with an invalid file type.
    """
    try:
        async def async_test():
            # Your async code here
            headers = Headers({"Content-Type": "application/json"})
            await verify_png_image(file=UploadFile(filename="test.txt", headers=headers, file=io.BytesIO(b"asdf")))
            assert False, "This should not be reached."

        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_test())
    except UserUpdateError as e:
        assert str(e) == "400: Invalid file type. Only PNG images are accepted."


def test_invalid_mime_type():
    """
    Test the verify_png_image method with an invalid mime type.
    """
    try:
        async def async_test():
            # Your async code here
            headers = Headers({"Content-Type": "image/png"})
            await verify_png_image(file=UploadFile(filename="test.png", headers=headers, file=io.BytesIO(b"asdf")))
            assert False, "This should not be reached."

        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_test())
    except UserUpdateError as e:
        assert str(e) == "400: Invalid file type. Only PNG images are accepted."


def test_invalid_file_size():
    """
    Test the verify_png_image method with an invalid file size.
    """
    try:
        async def async_test():
            # Your async code here
            headers = Headers({"Content-Type": "text/html"})
            await verify_png_image(file=UploadFile(filename="test.png",
                                                   headers=headers,
                                                   file=io.BytesIO(b"00000")))
            assert False, "This should not be reached."

        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_test())
    except UserUpdateError as e:
        assert str(e) == "400: Invalid file type. Only PNG images are accepted."


def test_invalid_png_image():
    """
    Test the verify_png_image method with an invalid PNG image.
    """
    try:
        async def async_test():
            # Your async code here
            headers = Headers({"Content-Type": "image/png"})
            await verify_png_image(file=UploadFile(filename="test.png",
                                                   headers=headers,
                                                   file=io.BytesIO(b"0" * 1024)))
            assert False, "This should not be reached."

        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_test())
    except UserUpdateError as e:
        assert str(e) == "400: Invalid file type. Only PNG images are accepted."


def test_valid_png_image():
    """
    Test the verify_png_image method with a valid PNG image.
    """
    async def async_test():
        # Your async code here
        headers = Headers({"Content-Type": "image/png"})
        result = await verify_png_image(file=UploadFile(filename="test.png",
                                                     headers=headers,
                                                     file=io.BytesIO(b'\x89PNG\r\n\x1a\n' + b"0" * 1024)))
        assert result == b'\x89PNG\r\n\x1a\n' + b"0" * 1024

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_test())
