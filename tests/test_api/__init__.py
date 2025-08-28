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

import json
import functools
from datetime import date
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from fastapi.responses import PlainTextResponse
from fastapi.exceptions import RequestValidationError
from routers import add_routes
from core.idp import IdentityProviderBase
from schema import engine
from schema.user import User, UserTest
from sqlalchemy.orm import Session
from core.auth import GuardianRoleEnum, UserUpdateError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import List

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

# We start up the app in test mode.
app = FastAPI()
add_routes(app)


TEST_EMAIL = "test@test.com"

# These access credentials are exclusively used by pytest for testing authentication.
TEST_USERS = {item.name: UserTest(email=f"{item.name}@test.local",
                                  full_name=item.name,
                                  roles=[item],
                                  locked=False,
                                  active_from=date.today()) for item in GuardianRoleEnum}
TEST_EMAILS = [item.email for item in TEST_USERS.values()]


def get_test_user(user_name: GuardianRoleEnum) -> UserTest:
    """
    Helper to query a test user.
    """
    return get_test_users(user_names=[user_name])[0]


def get_test_users(user_names: List[GuardianRoleEnum] = None,
                   roles: List[GuardianRoleEnum] = None,
                   exclude: bool = False) -> List[UserTest]:
    """
    Helper to query test users.
    """
    if user_names:
        names = [item.name for item in user_names]
        result = [value for name, value in TEST_USERS.items() if (not exclude and name in names) or (exclude and name not in names)]
    elif roles:
        result = []
        for name, value in TEST_USERS.items():
            for role in value.roles:
                if (not exclude and role in roles) or (exclude and role not in roles):
                    result.append(value)
                    break
    else:
        raise ValueError()
    return result


def init_test_users():
    """
    Initializes all test user accounts.
    """
    with Session(engine) as session:
        # We register all users in the database and create a bearer token for each of them.
        for _, user in TEST_USERS.items():
            db_user = User(**user.dict())
            user.bearer = IdentityProviderBase.create_token_for_user(session=session, claim_user=db_user)
        session.commit()
        # We obtain the user ids from the database.
        for _, user in TEST_USERS.items():
            db_user = session.query(User).filter(User.email == user.email).one()
            user.id = db_user.id


def delete_users(function):
    """
    Decorator that deletes all users before running the test.
    """
    @functools.wraps(function)
    def wrapper():
        with Session(engine) as session:
            session.query(User).filter(User.email.notin_(TEST_EMAILS)).delete()
            session.commit()
        function()
    return wrapper


def assert_dict(dict1: dict | str,
                dict2: dict | str,
                equal_attributes: list = [],
                ignore_attributes: list = []):
    """
    Compares the given dicts. Keys that are in list equal_attributes must be equal. If they are not in the
    equal_attributes list and not in the ignore_attributes list, then they must differ.

    :param: The first dict that is compared.
    :param: The second dict that is compared.
    :param: List of attributes that must be equal.
    :param: List of attributes that should be ignored.
    """
    dict1_tmp = dict1 if isinstance(dict1, dict) else json.loads(dict1)
    dict2_tmp = dict2 if isinstance(dict2, dict) else json.loads(dict2)
    for key, value in dict1_tmp.items():
        if key in ignore_attributes:
            continue
        if key in equal_attributes:
            if value != dict2_tmp[key]:
                print(f"{value} != {dict2_tmp[key]} ({key})")
            assert value == dict2_tmp[key]
        else:
            if value == dict2_tmp[key]:
                print(f"{value} == {dict2_tmp[key]} ({key})")
            assert value != dict2_tmp[key]


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    if isinstance(exc, UserUpdateError):
        return PlainTextResponse(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
    return PlainTextResponse("Incomplete or invalid data", status_code=status.HTTP_400_BAD_REQUEST)

client = TestClient(app)
