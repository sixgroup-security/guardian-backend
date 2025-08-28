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

import uuid
import pytest
from typing import Dict, Set
from datetime import date
from sqlalchemy.orm import Session
from schema.user import User, UserTest, UserRead
from schema.util import GuardianRoleEnum
from core.idp import IdentityProviderBase
from core.auth import AuthenticationError

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_user_fixture():
    """
    Fixture factory/closure that provides a function to create a new user.
    """
    def _get_user(
        roles: Set[GuardianRoleEnum] | None,
        full_name: str | None = None,
        email: str | None = None,
        active_from: date | None = None,
        active_until: date | None = None,
        locked: bool | None = False,
    ) -> Dict:
        data = {
            "email": email if email else f"{str(uuid.uuid4())}@{str(uuid.uuid4())}.com",
            "locked": locked,
            "full_name": full_name if full_name else str(uuid.uuid4()),
            "roles": roles,
            "active_from": active_from if active_from else date.today(),
            "active_until": active_until,
        }
        return data
    yield _get_user


@pytest.fixture
def create_user_fixture(get_user_fixture):
    """
    Fixture factory/closure that creates a new user in the database.
    """
    def _create_customer(
            session: Session,
            **kwargs,
    ) -> User:
        # Create customer
        user_dict = get_user_fixture(**kwargs)
        user = User(**user_dict)
        if not session.query(User).filter_by(email=user.email).one_or_none():
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    yield _create_customer


@pytest.fixture
def create_test_user_fixture(create_user_fixture, delete_user_fixture):
    """
    Fixture that creates a user for testing the token.
    """
    def _create_test_user(session: Session, **kwargs):
        user = create_user_fixture(session=session, **kwargs)
        test_user = UserTest(**user.dict())
        try:
            test_user.bearer = IdentityProviderBase.create_token_for_user(session=session, claim_user=user)
            session.commit()
        except AuthenticationError as ex:
            delete_user_fixture(session=session, user=user)
            raise ex
        return test_user
    yield _create_test_user


@pytest.fixture
def delete_user_fixture():
    """
    Fixture factory/closure that provides a function to delete a user.
    """
    def _delete_user(session: Session, user: User | UserTest | UserRead):
        session.query(User).filter_by(id=user.id).delete()
        session.commit()
    yield _delete_user
