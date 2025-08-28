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

import logging
from abc import abstractmethod
from httpx import Response
from typing import Tuple, List
from fastapi import status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from core.auth import AuthenticationError, Token, create_access_token
from core.config import settings
from schema.user import JsonWebToken as UserToken
from schema.user import User, TokenType
from schema.util import update_database_record, sha256

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


class IdentityProviderBase:

    def __init__(
            self,
            response: Response,
            client_ip: str | None
    ):
        if response.status_code != status.HTTP_200_OK:
            logger.error(f"Failed to obtain access token from OpenID Connect provider. Response: {response.content}")
            raise AuthenticationError("Failed to obtain access token from IdP.")
        self._response = response
        self._token_data = response.json()
        self._client_ip = client_ip

    @staticmethod
    def create_token(
            session: Session,
            user: User,
            token_type: TokenType,
            expires: datetime.date,
            token_name: str | None = None,
            scopes: List[str] | None = None,
    ) -> Tuple[UserToken, str]:
        """
        This method creates a new token.
        """
        access_token = create_access_token(
            data={
                "sub": user.email,
                "scopes": scopes or user.scopes_str,
                "name": token_name,
                "type": token_type.name
            },
            expires=expires,
        )
        # We add the new access token to the database.
        token = UserToken(
            user=user,
            name=token_name,
            type=token_type,
            revoked=False,
            expiration=expires,
            value=sha256(access_token)
        )
        session.add(token)
        return token, access_token

    @staticmethod
    def create_token_for_user(session: Session, claim_user: User) -> Token:
        """
        This method performs all necessary checks
        """
        # If the user does not have any roles, then we do not allow it to log in.
        if len(claim_user.roles) == 0:
            raise AuthenticationError("You are not authorized to access this application.")
        # Check if the user exists and is active. If it exists, then we update its roles.
        user = session.query(User).filter_by(email=claim_user.email).first()
        if not user:
            user = claim_user
            user.last_login = datetime.now()
            session.add(user)
        else:
            # If the user is inactive, then we do not allow it to log in.
            if not user.is_active:
                raise AuthenticationError("You are not authorized to access this application.")
            claim_user.id = user.id
            # TODO: If the user was a pentester, leadpentester or customer and these roles changed somehow, then we need to remove all his project access permissions.
            user = update_database_record(
                session=session,
                source=claim_user,
                source_model=User,
                query_model=User,
                commit=False,
                exclude_unset=True
            )
            # We have to save in local time because PostgreSQL will convert and store it to UTC.
            user.last_login = datetime.now()
            # We revoke all previously active user tokens.
            session.query(UserToken) \
                .filter(
                    and_(
                        UserToken.user_id == user.id,
                        UserToken.type == TokenType.user,
                        UserToken.revoked == False
                    )
                ).update({UserToken.revoked: True})
        # Finally, we create a valid token for the user.
        access_token_expires = timedelta(minutes=settings.oauth2_access_token_expire_minutes)
        _, access_token = IdentityProviderBase.create_token(
            session=session,
            user=user,
            token_type=TokenType.user,
            expires=datetime.utcnow() + access_token_expires
        )
        # TODO: Here we need to add the user's access permissions to certain projects/resources.
        return access_token

    @abstractmethod
    async def get_token(self, session: Session):
        ...
