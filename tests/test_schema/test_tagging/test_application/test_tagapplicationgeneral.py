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

from schema import TagApplicationGeneral, TagCategoryEnum, Application

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


def test_delete_application(
        create_tag_fixture,
        create_application_fixture,
        db_session
):
    """
    Tests whether the delete method of a TagApplicationGeneral instance works correctly.
    """
    session, _ = db_session
    # Setup data
    tag = create_tag_fixture(
        session=session,
        categories={TagCategoryEnum.application, TagCategoryEnum.general}
    )
    application = create_application_fixture(session=session)
    application.general_tags.append(tag)
    session.commit()
    assert session.query(TagApplicationGeneral).filter_by(
        application_id=application.id,
        tag_id=tag.id
    ).count() == 1
    # Delete application
    session.query(Application).filter_by(id=application.id).delete()
    session.commit()
    # Check if the tag application was deleted
    assert session.query(TagApplicationGeneral).filter_by(
        application_id=application.id,
        tag_id=tag.id
    ).count() == 0

