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

import uuid
import pytest
from typing import Dict, Set

from schema import TagCategoryEnum, Tag
from sqlalchemy import and_
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


@pytest.fixture
def get_tag_fixture(db_session):
    """
    Fixture factory/closure that provides a function to create a new tag.
    """
    session, _ = db_session

    def get_create_tag(
            categories: Set[TagCategoryEnum],
            name: str | None = None,
    ) -> Dict:
        data = {
            "name": name if name else str(uuid.uuid4()),
            "categories": categories
        }
        return data
    yield get_create_tag


@pytest.fixture
def create_tag_fixture(get_tag_fixture):
    """
    Fixture factory/closure that creates a new tag in the database.
    """
    def _create_tag(
            session: Session,
            **kwargs,
    ) -> Tag:
        # Create customer
        tag_dict = get_tag_fixture(**kwargs)
        tag = Tag(**tag_dict)
        if not session.query(Tag) \
            .filter(
                and_(
                    Tag.name == tag.name,
                    Tag.categories.contains(tag.categories)
                )
        ).one_or_none():
            session.add(tag)
            session.commit()
            session.refresh(tag)
        return tag
    yield _create_tag
