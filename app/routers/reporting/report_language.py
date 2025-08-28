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

from __future__ import annotations

import logging
from uuid import UUID
from typing import Annotated, List
from fastapi import Body, Depends, APIRouter, Security, status
from sqlalchemy.orm import Session
from core.config import API_PREFIX
from schema import get_db
from schema.util import (
    ApiPermissionEnum, get_all, get_by_id, update_database_record, StatusMessage, StatusEnum, InvalidDataError,
    NotFoundError
)
from schema.reporting.report_language import (
    ReportLanguage, ReportLanguageRead, ReportLanguageUpdate, ReportLanguageCreate, ReportLanguageLookup
)
from routers.user import User, get_current_active_user, get_logger

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_REPORT_LANGUAGE_SUFFIX = "/languages"
API_REPORT_LANGUAGE_PREFIX = API_PREFIX + API_REPORT_LANGUAGE_SUFFIX


router = APIRouter(
    prefix=API_REPORT_LANGUAGE_PREFIX,
    tags=["report language"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def get_report_language(language_id: UUID, session: Annotated[Session, Depends(get_db)]) -> ReportLanguage:
    """
    Get a report language by its ID.
    """
    return get_by_id(session, ReportLanguage, language_id)


def update_default(
        is_new: bool,
        report_language: ReportLanguageCreate | ReportLanguageCreate,
        session: Session
):
    """
    Checks if the given report language is the new default language and if so, make sure that any other default
    language is updated to be not default.

    :param is_new: Defines whether the calling function creates a new (True) or update an existing report language.
    :param report_language: The report language whose is_default attribute should be correctly updated.
    :param session: The database session used.
    """
    # TODO: Implement a database trigger for this check.
    count = session.query(ReportLanguage).count()
    if report_language.is_default:
        session.query(ReportLanguage).filter(ReportLanguage.is_default).update(
            {ReportLanguage.is_default: False})
    elif count == 0 and is_new or count == 1 and not is_new:
        report_language.is_default = True


@router.get("/lookup", response_model=List[ReportLanguageLookup])
def read_report_languages_lookup(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_language_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns a summary for all report languages.
    """
    return get_all(session, ReportLanguage).order_by(ReportLanguage.name).all()


@router.get("", response_model=List[ReportLanguageRead])
def read_report_languages(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_language_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all report languages.
    """
    return get_all(session, ReportLanguage).order_by(ReportLanguage.name).all()


@router.delete("/{language_id}", response_model=StatusMessage)
def delete_report_language(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_language_delete.name])],
    report_template: Annotated[UUID, Depends(get_report_language)],
    session: Session = Depends(get_db)
):
    """
    Deletes a report language by its ID.
    """
    session.delete(report_template)
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Record successfully deleted."
    )


@router.post("", response_model=ReportLanguageRead)
def create_report_language(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_language_create.name])],
    template: Annotated[ReportLanguageCreate, Body],
    session: Session = Depends(get_db)
):
    """
    Creates a new report language.
    """
    try:
        new = ReportLanguage(**template.model_dump())
        new.language_code = new.language_code.lower()
        update_default(True, new, session)
        session.add(new)
        session.commit()
        session.refresh(new)
        return new
    except Exception as e:
        raise InvalidDataError(str(e))


@router.put("", response_model=ReportLanguageRead)
def update_report_language(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.report_language_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[ReportLanguageUpdate, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a report language.
    """
    try:
        item.language_code = item.language_code.lower()
        update_default(False, item, session)
        return update_database_record(
            session=session,
            source=item,
            source_model=ReportLanguageUpdate,
            query_model=ReportLanguage,
            commit=True,
            by_alias=True
        )
    except NotFoundError as ex:
        logger.exception(ex)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))
