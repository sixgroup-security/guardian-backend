"""
This file defines and documents all FastAPI endpoints for API token management.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Annotated, List
from fastapi import Depends, APIRouter, status, Security, Body
from sqlalchemy.orm import Session
from routers.user import get_current_active_user
from schema import get_db
from schema.user import (
    JsonWebToken, User, TokenType, JsonWebTokenRead, JsonWebTokenReadTokenValue, JsonWebTokenCreate, JsonWebTokenUpdate
)
from schema.util import ApiPermissionEnum, InvalidDataError, StatusMessage, StatusEnum, ROLE_API_PERMISSIONS, \
    AuthorizationError
from core.idp import IdentityProviderBase
from core.config import API_PREFIX

logger = logging.getLogger(__name__)

API_APPLICATION_SUFFIX = "/tokens"
API_APPLICATION_PREFIX = API_PREFIX + API_APPLICATION_SUFFIX

router = APIRouter(
    prefix=API_APPLICATION_PREFIX,
    tags=["access tokens"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Incomplete or invalid data"},
        404: {"description": "Not found"},
        500: {"description": "Internal Server Error"}
    }
)


@router.get("", response_model=List[JsonWebTokenRead])
async def get_user_tokens(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.access_token_read.name])],
        session: Annotated[Session, Depends(get_db)]
):
    """
    Retrieves a list of all tokens issued to the current user.
    """
    return session.query(JsonWebToken).filter_by(user_id=current_user.id, type=TokenType.api).all()


@router.post("", response_model=JsonWebTokenReadTokenValue)
async def create_new_token(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.access_token_create.name])],
        session: Annotated[Session, Depends(get_db)],
        item: Annotated[JsonWebTokenCreate, Body]
):
    """
    Generates a new JWT API token for the current user. The token's expiration time can be specified.
    """
    try:
        scopes = []
        # Obtain all user permissions
        for role in current_user.roles:
            scopes += [item.get("id", "") for item in ROLE_API_PERMISSIONS[role.name]]
        # Ensure that only permissions within the user's privileges are requested.
        for scope in item.scope:
            if scope not in scopes:
                raise AuthorizationError()
        if current_user.get_access_token(item.name):
            raise InvalidDataError("Access token with this name exists already.")
        # Validate the provided expiration date
        if item.expiration and item.expiration <= datetime.now():
            raise InvalidDataError("Expiration time must be in the future")
        if len(item.scope or []) == 0:
            raise InvalidDataError("The access token must contain at least one permission")
        # Create new JWT
        user = session.query(User).filter_by(id=current_user.id).one()
        new_jwt_token, raw_jwt_token = IdentityProviderBase.create_token(
            session=session,
            token_name=item.name,
            user=user,
            token_type=TokenType.api,
            expires=item.expiration,
            scopes=item.scope
        )
        session.commit()
        session.refresh(new_jwt_token)
        # We need to return the actual JWT
        new_jwt_token.value = raw_jwt_token
        return new_jwt_token
    except InvalidDataError as e:
        logger.exception(e)
        raise e
    except Exception as e:
        logger.exception(e)
        raise InvalidDataError("Failed to generate access token.")


@router.put("", response_model=StatusMessage)
async def update_access_token(
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.access_token_update.name])],
        session: Annotated[Session, Depends(get_db)],
        item: Annotated[JsonWebTokenUpdate, Body]
):
    """
    Updates a specific access token ty its ID.
    """
    if token := session.query(JsonWebToken).filter_by(
            id=item.id,
            type=TokenType.api,
            user_id=current_user.id
    ).one_or_none():
        token.revoked = item.revoked
        session.add(token)
        session.commit()
    return StatusMessage(
        status=status.HTTP_204_NO_CONTENT,
        severity=StatusEnum.success,
        message=f"Access token successfully updated."
    )


@router.delete("/{token_id}", response_model=StatusMessage)
async def delete_token(
        token_id: uuid.UUID,
        current_user: Annotated[User, Security(get_current_active_user, scopes=[ApiPermissionEnum.access_token_delete.name])],
        session: Annotated[Session, Depends(get_db)]
):
    """
    Deletes a specific access token by its ID.
    """
    if token := session.query(JsonWebToken).filter_by(
            id=token_id,
            type=TokenType.api,
            user_id=current_user.id
    ).one_or_none():
        session.delete(token)
        session.commit()
    return StatusMessage(
        status=status.HTTP_204_NO_CONTENT,
        severity=StatusEnum.success,
        message=f"Access token successfully deleted."
    )
