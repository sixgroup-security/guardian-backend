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

from __future__ import annotations

import jose
import logging
from uuid import UUID
from sqlmodel import SQLModel
from typing import Annotated, Dict, List, Tuple, Type, Callable
from fastapi import Body, Depends, Response, Header, Security, APIRouter, UploadFile, File, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import JWTError, jwt
from fastapi.security import SecurityScopes
from pydantic import ValidationError
from routers.util import verify_png_image
from schema import get_db
from schema.util import (
    ApiPermissionEnum, GuardianRoleEnum, get_all, get_by_id, update_database_record, sha256, StatusMessage,
    StatusEnum, UserLookup, NotFoundError, InvalidDataError, ROLE_API_PERMISSIONS
)
from schema.user import (
    User, UserRead, UserReadMe, UserUpdateAdmin, TokenType, TableDensityType, JsonWebToken as UserToken,
    NotificationRead, Notification, UserType
)
from schema.reporting.report_language import ReportLanguage
from core.auth import oauth2_scheme, AuthenticationError, UserUpdateError
from core.config import API_PREFIX, settings
from sqlalchemy import or_, and_, not_
from sqlalchemy.orm import Session
from routers.util import get_project_years

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

API_USER_SUFFIX = "/users"
API_USER_PREFIX = API_PREFIX + API_USER_SUFFIX

logger = logging.getLogger(__name__)

security = HTTPBasic()
router = APIRouter(
    prefix=API_USER_PREFIX,
    tags=["user"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


def get_user(user_id: UUID, session: Annotated[Session, Depends(get_db)]):
    """
    Get a user by its ID.
    """
    return get_by_id(session, User, user_id)


def get_report_language(language_id: UUID, session: Annotated[Session, Depends(get_db)]) -> SQLModel:
    """
    Get a report language by its ID.
    """
    return get_by_id(session, ReportLanguage, language_id)


def verify_token(session: Session, x_real_ip: List[str], token: str) -> Tuple[Type[User], dict]:
    """
    Verifies the integrity of the given token.
    """
    # Check 1: Verify the integrity of the token.
    try:
        if not token:
            raise AuthenticationError()
        payload = jwt.decode(token, settings.oauth2_secret_key, algorithms=[settings.oauth2_algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise AuthenticationError()
    except jose.exceptions.ExpiredSignatureError:
        raise AuthenticationError()
    except (JWTError, ValidationError) as ex:
        logger.exception(ex)
        raise AuthenticationError()
    # Check 2: Check whether the user exists and is active.
    user = session.query(User).filter_by(email=email).first()
    if user is None or not user.is_active or not user.roles:
        raise AuthenticationError("Your account has been locked. Please contact the administrator.")
    # Check 3: Check whether the user's token has been revoked.
    access_token = session.query(UserToken) \
        .filter(
            and_(
                UserToken.user_id == user.id,
                or_(UserToken.type == TokenType.user, UserToken.type == TokenType.api),
                UserToken.value == sha256(token),
                not_(UserToken.revoked)
            )
        ).first()
    if access_token is None or access_token.revoked:
        raise AuthenticationError("Token has been revoked. Please login again.")
    return user, payload


def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_db)],
    x_real_ip: list[str] | None = Header(default=None)
) -> Type[User]:
    """
    Verifies the given token and returns the user if the token is valid and the user exists.
    """
    user, payload = verify_token(session, x_real_ip, token)
    # Check 2: Check whether the token contains one of the required scopes.
    scoping_results = [scope in security_scopes.scopes for scope in payload.get("scopes", [])]
    if not any(scoping_results):
        logger.critical(f"User {user.email} tried to access scopes {security_scopes.scope_str}.")
        raise AuthenticationError("Could not validate user.")
    # Check 3: Check whether the user's IP address has changed.
    # if x_real_ip and x_real_ip[0] != user.client_ip:
    #     logger.warning(f"User {user.email} tried to access the application from a different IP address.")
    #     session.query(User).filter_by(id=user.id).update({"client_ip": x_real_ip[0]})
    return user


def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)]
):
    """
    This function verifies that the given user is active.
    """
    # We checked this already during login and only if the user is active we return the token.
    if not current_user.is_active:
        raise AuthenticationError()
    return current_user


def get_basic_authentication_user(
    security_scopes: SecurityScopes,
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    session: Annotated[Session, Depends(get_db)],
    x_real_ip: list[str] | None = Header(default=None)
):
    """
    Implements Basic authentication via JWT authentication. This is required by PowerBI.
    """
    user, payload = verify_token(session, x_real_ip, credentials.password)
    # Check 1: Ensure that the token is an API token.
    if payload.get("type", "").lower() != "api":
        logger.critical(f"Provided token is not an API token.")
        raise AuthenticationError("Could not validate user.")
    # Check 2: Check whether the token contains one of the required scopes.
    scoping_results = [scope in security_scopes.scopes for scope in payload.get("scopes", [])]
    if not any(scoping_results):
        logger.critical(f"User {user.email} tried to access scopes {security_scopes.scope_str}.")
        raise AuthenticationError("Could not validate user.")
    # Check 3: Check whether the user's IP address has changed.
    # if x_real_ip and x_real_ip[0] != user.client_ip:
    #     logger.warning(f"User {user.email} tried to access the application from a different IP address.")
    #     session.query(User).filter_by(id=user.id).update({"client_ip": x_real_ip[0]})
    return user


def get_logger() -> logging.Logger:
    """
    Returns a logger with the current user injected.
    """
    # TODO: Add user to logger. Eventually, we merge this with get_current_active_user and this method will then
    #       return an object containing the logger and the user.
    return logging.getLogger(__name__)


def process_user_notification(
        current_user: User,
        notification_id: UUID,
        session: Session,
        process_fn: Callable[[UUID, Session], None]
):
    """
    Processes a user notification.
    """
    notification = session.query(Notification).filter_by(id=notification_id).one_or_none()
    if notification and notification.user_id == current_user.id:
        process_fn(notification_id, session)
    return current_user.notifications


@router.get("/me", response_model=UserReadMe)
def read_me(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Allows users to obtain their user information.
    """
    if not current_user.report_language_id:
        user = session.query(User).filter_by(id=current_user.id).one()
        user.report_language = session.query(ReportLanguage).filter_by(is_default=True).one_or_none()
        session.commit()
        session.refresh(user)
        return user
    return current_user


@router.get("/me/settings/avatar")
async def get_avatar(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_read.name])],
):
    """
    Allows users to request their avatar.
    """
    if not current_user.avatar:
        return
    return Response(content=current_user.avatar, media_type="image/png")


@router.get("/me/settings/{guid}", response_model=Dict)
def read_user_datagrid_settings(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_read.name])],
    guid: UUID,
):
    """
    Allows users to obtain a specific MUI DataGrid configuration.
    """
    result = {}
    str_guid = str(guid)
    if current_user.settings and str_guid in current_user.settings:
        result = current_user.settings[str_guid]
    return result


@router.get("/me/api-permissions", response_model=List[Dict[str, str]])
def get_access_token_permissions(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_read.name])],
):
    """
    Allows users to obtain potential access token permissions.
    """
    if GuardianRoleEnum.api not in current_user.roles and GuardianRoleEnum.admin not in current_user.roles:
        return []
    result = set()
    for role in current_user.roles:
        info = ROLE_API_PERMISSIONS[role.name]
        result.update(tuple(item.items()) for item in info)
    return [dict(tup) for tup in sorted(result)]


@router.get("", response_model=List[UserRead])
def read_users(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.user_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all users.
    """
    return get_all(session, User).filter(User.type != UserType.legacy).order_by(User.full_name).all()


@router.get("/managers", response_model=List[UserLookup])
def read_managers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.user_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all managers.
    """
    return session.query(User) \
        .filter(
            and_(
                not_(User.locked),
                User.show_in_dropdowns,
                User.roles.contains([GuardianRoleEnum.manager])
            )
        ).order_by(User.full_name).all()


@router.get("/customers", response_model=List[UserLookup])
def read_customers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.user_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all customers.
    """
    return session.query(User) \
        .filter(
            and_(
                not_(User.locked),
                User.show_in_dropdowns,
                User.roles.contains([GuardianRoleEnum.customer])
            )
        ).order_by(User.full_name).all()


@router.get("/pentesters", response_model=List[UserLookup])
def read_penetration_testers(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.user_read.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Returns all penetration testers.
    """
    return session.query(User) \
        .filter(
            and_(
                not_(User.locked),
                User.show_in_dropdowns,
                or_(
                    User.roles.contains([GuardianRoleEnum.pentester]),
                    User.roles.contains([GuardianRoleEnum.leadpentester])
                )
            )
        ).order_by(User.full_name).all()


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    _: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.user_read.name])],
    selected_user: Annotated[User, Depends(get_user)]
):
    """
    Returns a user by its ID.
    """
    return selected_user


@router.put("/me/settings/avatar", response_model=UserRead)
async def update_my_avatar(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    file: UploadFile = File(...),
    session: Session = Depends(get_db)
):
    """
    Allows users to update their avatar.
    """
    image_data = await verify_png_image(file, max_file_size=1024 ** 2)
    # We cannot query the user and assign the avatar then because this results in an encoding error. As a workaround,
    # we update the avatar directly in the database.
    user = session.query(User).filter_by(id=current_user.id).one()
    user.avatar = image_data
    session.commit()
    session.refresh(user)
    return user


@router.put("/me/settings/avatar/reset")
async def reset_my_avatar(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    session: Annotated[Session, Depends(get_db)]
):
    """
    Allows users to reset their avatar.
    """
    session.query(User).filter_by(id=current_user.id).update({"avatar": None})
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Avatar successfully removed."
    )


@router.put("/me/settings/lightmode/{mode}", response_model=StatusMessage)
def update_my_preferred_visual_mode(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    mode: bool,
    session: Session = Depends(get_db)
):
    """
    Allows users to switch between light and dark mode.
    """
    session.query(User).filter_by(id=current_user.id).update({"light_mode": mode})
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"User settings updated."
    )


@router.put("/me/settings/toggle-menu", response_model=StatusMessage)
def update_my_toggle_menu_setting(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    session: Session = Depends(get_db)
):
    """
    Allows users to toggle their React sidebar.
    """
    user = session.query(User).filter_by(id=current_user.id).one()
    user.toggle_menu = not user.toggle_menu
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"User settings updated."
    )


@router.put("/me/settings/selected-year/{year}", response_model=StatusMessage | None)
def update_my_preferred_year(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    year: str,
    session: Session = Depends(get_db)
):
    """
    Allows users to update their selected year.
    """
    years = get_project_years(session=session)
    if year in years:
        if year == "All":
            year = None
        session.query(User).filter_by(id=current_user.id).update({"selected_year": year})
        session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"User settings updated."
    )


@router.put("/me/settings/table-density/{density}", response_model=StatusMessage)
def update_my_preferred_table_density(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    logger: Annotated[logging.Logger, Depends(get_logger)],
    density: str,
    session: Session = Depends(get_db)
):
    """
    Allows users to update their MUI DataGrid table density.
    """
    try:
        density = TableDensityType[density]
        session.query(User).filter_by(id=current_user.id).update({"table_density": density})
        session.commit()
        return StatusMessage(
            status=status.HTTP_200_OK,
            severity=StatusEnum.success,
            message=f"User settings updated."
        )
    except Exception as ex:
        logger.exception(ex)
        return StatusMessage(
            status=status.HTTP_400_BAD_REQUEST,
            severity=StatusEnum.error,
            message=f"Updating user settings failed."
        )


@router.put("/me/settings/report-language/{language_id}", response_model=StatusMessage)
def update_my_preferred_report_language(
    current_user: Annotated[User, Security(get_current_user,
                                           scopes=[ApiPermissionEnum.user_me_report_language_update.name])],
    language: Annotated[UUID, Depends(get_report_language)],
    session: Session = Depends(get_db)
):
    """
    Allows users to update their preferred report language.
    """
    session.query(User).filter_by(id=current_user.id).update({"report_language_id": language.id})
    session.commit()
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"User settings updated."
    )


@router.put("/me/settings/{guid}", response_model=Dict)
def update_user_datagrid_settings(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    guid: UUID,
    setting: Dict,
    session: Session = Depends(get_db)
):
    """
    Allows users to update a specific MUI DataGrid configuration.
    """
    str_guid = str(guid)
    if len(current_user.settings) > 30:
        raise UserUpdateError("You cannot store more than 30 settings.")
    # TODO: Limit Dict size as well
    # Make sure preference panels are not stored. This ensures that any DataGrid dialogs are not constantly open.
    if "preferencePanel" in setting:
        del setting["preferencePanel"]
    # We have to query in the same session to avoid a detached instance error.
    # current_user.settings[str_guid] = setting
    # update_database_record(session=session, source=current_user, source_model=User, query_model=User, commit=True)
    user = session.query(User).filter_by(id=current_user.id).one()
    settings_dict = dict(user.settings)
    settings_dict[str_guid] = setting
    user.settings = settings_dict
    session.add(user)
    session.commit()
    return setting


@router.put("", response_model=UserRead)
def update_user(
    _: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_update.name])],
    local_logger: Annotated[logging.Logger, Depends(get_logger)],
    item: Annotated[UserUpdateAdmin, Body],
    session: Session = Depends(get_db)
):
    """
    Updates a user.
    """
    try:
        return update_database_record(
            session=session,
            source=item,
            source_model=UserUpdateAdmin,
            query_model=User,
            commit=True
        )
    except NotFoundError as e:
        local_logger.exception(e)
        return item
    except Exception as e:
        raise InvalidDataError(str(e))


@router.get("/me/notifications", response_model=List[NotificationRead])
def get_user_notifications(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_read.name])],
):
    """
    Allows users to obtain their notifications.
    """
    return current_user.notifications


@router.delete("/me/notifications/{notification_id}", response_model=StatusMessage)
def get_user_notifications(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    notification_id: UUID,
    session: Session = Depends(get_db),
):
    """
    Allows users to delete their notifications.
    """
    def delete_notification(notification_id: UUID, session: Session):
        session.query(Notification).filter_by(id=notification_id).delete()
        session.commit()
    process_user_notification(current_user, notification_id, session, delete_notification)
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Notification successfully deleted."
    )


@router.put("/me/notifications/{notification_id}/toggle-read", response_model=StatusMessage)
def get_user_notifications(
    current_user: Annotated[User, Security(get_current_user, scopes=[ApiPermissionEnum.user_me_update.name])],
    notification_id: UUID,
    session: Session = Depends(get_db),
):
    """
    Allows users to mark their notifications as read/unread.
    """
    def toggle_notification_read(notification_id: UUID, session: Session):
        notification = session.query(Notification).filter_by(id=notification_id).one()
        notification.read = not notification.read
        session.commit()
    process_user_notification(current_user, notification_id, session, toggle_notification_read)
    return StatusMessage(
        status=status.HTTP_200_OK,
        severity=StatusEnum.success,
        message=f"Notification successfully updated."
    )
