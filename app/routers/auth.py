"""
This file defines and documents all FastAPI endpoints for authentication.
"""
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

import httpx
import logging
from core.auth import oauth2_scheme, AuthenticationError, IdpConnectionError
from typing import Annotated, Union, List
from fastapi import Depends, APIRouter, Header, Security, status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from routers.user import get_current_user
from schema import get_db
from schema.util import ApiPermissionEnum
from schema.user import JsonWebToken as UserToken
from schema.user import User, TokenType
from core.config import settings, COOKIE_NAME
from fastapi.responses import RedirectResponse
from core.idp.factory import IdentityProviderFactory

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["auth"]
)


@router.get("/redirect-login")
async def redirect_login():
    """
    Redirects the user to the OpenID Provider's authorization page.
    """
    # Redirect the user to the OpenID Provider's authorization page
    authorization_url = f"{settings.authorization_url}?response_type=code&client_id={settings.client_id}&redirect_uri={settings.redirect_uri}"
    return RedirectResponse(authorization_url)


@router.get("/callback")
async def callback(
        code: str,
        session: Annotated[Session, Depends(get_db)],
        x_real_ip: Annotated[Union[List[str], None], Header()] = None
):
    """
    Callback function for the OpenID Connect.
    """
    try:
        # Exchange the authorization code for an access token
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.redirect_uri,
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
        }
        # Verify user
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.token_url, data=data)
        if response.status_code != 200:
            raise IdpConnectionError()
        provider = IdentityProviderFactory.get(
            settings.idp_type,
            client_ip=x_real_ip[0] if x_real_ip else None,
            response=response
        )
        token = await provider.get_token(session=session)
        session.commit()
        # Finally, we create and return the HTTP response.
        response = RedirectResponse("/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        response.set_cookie(
            COOKIE_NAME,
            str(token),
            httponly=True,
            secure=settings.https,
            samesite="strict",
            path="/api"
        )
        return response
    except ValueError as e:
        logger.exception(e)
        return RedirectResponse(
            f"/login?msg={str(e)}",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except AuthenticationError as e:
        logger.error(e)
        return RedirectResponse(
            f"/login?msg={str(e.detail)}",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except IdpConnectionError as e:
        logger.error(e)
        return RedirectResponse(
            f"/login?msg={str(e.detail)}",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        logger.error(e)
        return RedirectResponse(
            "/login?msg=A general error occurred while logging in. Please try again.",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )


@router.get("/logout")
async def logout(
        token: Annotated[str, Depends(oauth2_scheme)],
        current_user: Annotated[User, Security(get_current_user, scopes=[item.name for item in ApiPermissionEnum])],
        session: Annotated[Session, Depends(get_db)]
):
    """
    Invalidates the current token.
    """
    response = RedirectResponse("/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.delete_cookie(COOKIE_NAME)
    # We revoke the current token.
    session.query(UserToken) \
        .filter(
            and_(
                UserToken.user_id == current_user.id,
                UserToken.type == TokenType.user
            )
        ).update({UserToken.revoked: True})
    session.commit()
    return response
