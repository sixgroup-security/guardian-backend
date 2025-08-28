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
# along with Guardian. If not, see <https://www.gnu.org/licenses/>.

import re
import uuid
import asyncio
import logging
from io import StringIO
from dotenv import load_dotenv
# We specify the environment to be used.
load_dotenv(stream=StringIO("ENV=prod"))
from core.config import settings
from fastapi import FastAPI, status
from routers import add_routes, CustomHeaderMiddleware
from routers.websocket import notify_user_listener
from schema import init_db
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from core import ExceptionWrapper
from contextlib import asynccontextmanager
# We need to import the scheduler to ensure jobs are regularly executed.
# from core import scheduler

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

# We set up a basic logger.
logging.basicConfig(
    filename=settings.log_file,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=settings.log_level
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This context manager is used to execute code before and after the FastAPI application is started.
    """
    # Startup events
    # Start listening to user notifications
    task = asyncio.create_task(notify_user_listener())
    # Initialize the database
    init_db(drop_tables=False, create_tables=False, load_data=False)
    yield
    # Shutdown events
    task.cancel()


app = FastAPI(
    title="Guardian API",
    lifespan=lifespan,
    openapi_url=None,
    docs_url=None,
    redoc_url=None
)
add_routes(app)
app.add_middleware(CustomHeaderMiddleware)

test = FastAPI(
    title="Guardian API",
    lifespan=lifespan
)
add_routes(test)
test.add_middleware(CustomHeaderMiddleware)


@app.exception_handler(StarletteHTTPException)
@test.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    error_code = str(uuid.uuid4())
    detail_message = exc.detail
    logger.exception(exc, extra={"error_code": error_code})

    if isinstance(exc, ExceptionWrapper):
        if isinstance(exc.orig, ValueError):
            detail_message = str(exc.orig)
        else:
            detail_message = "A duplicate key value violates a unique constraint."
            detail_search = re.search(r"DETAIL:  Key \((.*?)\)=\((.*?)\)", str(exc))
            if detail_search:
                detail_message = f"There is already an entry for column {detail_search.group(1).capitalize()} with " \
                                 f"value {detail_search.group(2)}."

    return JSONResponse({
        "status": exc.status_code,
        "severity": "error",
        "message": detail_message,
        "error_code": error_code
    }, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
@test.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    error_code = str(uuid.uuid4())
    logger.exception(exc, extra={"error_code": error_code})
    return JSONResponse({
        "status": status.HTTP_400_BAD_REQUEST,
        "severity": "error",
        "message": "Incomplete or invalid data",
        "error_code": error_code
    }, status_code=status.HTTP_400_BAD_REQUEST)


@app.exception_handler(Exception)
@test.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    error_code = str(uuid.uuid4())
    logger.exception(exc, extra={"error_code": error_code})
    return JSONResponse(
        {
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "type": "error",
            "message": f"Ops that should not happen 😳. Please contact the Guardian team and give them the following "
                       f"code: {error_code}",
            "error_code": error_code
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def main():
    """
    Run this module as a script. This is only useful for debugging purposes.
    """
    import uvicorn
    uvicorn.run("main:test", reload=True, port=8090, host="127.0.0.1")


if __name__ == "__main__":
    main()
