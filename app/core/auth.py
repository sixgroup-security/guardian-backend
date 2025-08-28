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

import httpx
import fastapi
import logging
from httpx import HTTPStatusError
from datetime import datetime
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from core.config import settings, COOKIE_NAME
from schema.util import GuardianRoleEnum, ApiPermissionEnum
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import BaseModel
from typing import Dict, List
from fastapi.security.utils import get_authorization_scheme_param
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


class OAuth2PasswordBearerWithCookie(fastapi.security.OAuth2):
    """
    This class enforces JWT authentication via cookie access_token.

    Source: https://github.com/tiangolo/fastapi/issues/796
    """
    def __init__(
            self,
            token_url: str,
            scheme_name: str | None = None,
            scopes: Dict[str, str] | None = None,
            auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password={
                "tokenUrl": token_url,
                "scopes": {key: value.description for key, value in scopes.items()}
            }
        )
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> str | None:
        authorization: str = request.cookies.get(COOKIE_NAME)
        authorization = f"Bearer {authorization}"
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


oauth2_scheme = OAuth2PasswordBearerWithCookie(
    token_url="/api/v1/token",
    scopes={item.name: item.value for item in ApiPermissionEnum},
)


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Could not validate user."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class IdpConnectionError(HTTPException):
    def __init__(self, detail: str = "Guardian server could not connect to IdP to obtain your claim. Please try "
                                     "again later."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class UserUpdateError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


def get_roles(roles: List[str]) -> List[GuardianRoleEnum]:
    """
    Get the roles from the given list of strings.
    """
    return [GuardianRoleEnum[role] for role in roles if role in GuardianRoleEnum.__members__]


async def verify_token(token: str):
    """
    Obtains the public key from the JWKS endpoint and verifies the given token.
    """
    try:
        # Fetch the public key from JWKS endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.jwks_url)
        if response.status_code != 200:
            raise IdpConnectionError()
        jwks = response.json()
        header = jwt.get_unverified_header(token)
        kid = header['kid']
        rsa_key = {}
        for key in jwks['keys']:
            if key['kid'] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if len(rsa_key) == 0:
            raise ValueError("No matching public key found.")
        payload = jwt.decode(
            token=token,
            key=rsa_key,
            algorithms=["RS256"],
            audience=settings.audience,
            issuer=settings.issuer
        )
        return payload
    except HTTPStatusError as e:
        logger.exception(e)
        raise IdpConnectionError() from e
    except Exception as e:
        logger.exception(e)
        raise AuthenticationError("It seems you are not authorized to access this application.") from e


def create_access_token(data: dict, expires: datetime):
    """
    Create an access token for the given data.
    :param data: The dict to be signed.
    :param expires: Date when the token expires.
    :return:
    """
    to_encode = data.copy()
    if expires:
        to_encode.update({"exp": expires})
    encoded_jwt = jwt.encode(to_encode, settings.oauth2_secret_key, algorithm=settings.oauth2_algorithm)
    return encoded_jwt
