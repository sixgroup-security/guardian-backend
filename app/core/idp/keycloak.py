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

import logging
from . import IdentityProviderBase
from core.auth import AuthenticationError, verify_token, get_roles
from core.config import settings
from schema.user import User
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


class KeycloakIdentityProvider(IdentityProviderBase):
    """
    Identity provider class to integrate Guardian with the identity provider Keycloak.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_user_from_token(self, claims: dict) -> User:
        """
        This method converts the token obtained from the identity provider to a user object.
        """
        # TODO: Implement generic logic that works for all identity providers.
        # TODO: We need to make sure that the user is authorized for the correct realm. At the moment, I assume this is done via the following check: claims["azp"] != settings.client_id
        if claims["azp"] != settings.client_id:
            raise AuthenticationError("The given access token was not issued for this application.")
        roles = claims["resource_access"][settings.client_id]["roles"]
        email = claims["email"]
        name = claims["name"]
        email_verified = claims["email_verified"]
        if not email_verified:
            raise AuthenticationError("Your email address has not been verified yet.")
        return User(
            email=email,
            roles=get_roles(roles),
            locked=False,
            full_name=name,
            client_ip=self._client_ip
        )

    async def get_token(self, session: Session):
        access_token = await verify_token(self._token_data["access_token"])
        user = self._get_user_from_token(access_token)
        token = self.create_token_for_user(session=session, claim_user=user)
        logger.info(f"User {user.email} successfully logged in.")
        return token
