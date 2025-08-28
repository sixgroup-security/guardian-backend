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
from . import IdentityProviderBase
from typing import Dict, List
from core.auth import AuthenticationError, verify_token
from core.config import settings
from schema.user import User
from schema.util import GuardianRoleEnum
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)


class AdfsIdentityProvider(IdentityProviderBase):
    """
    Identity provider class to integrate Guardian with the identity provider Microsoft Active Directory Federation
    Services.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _get_roles(claims: Dict) -> List[GuardianRoleEnum]:
        """
        This method extracts group membership information from the given access token and returns it as a list of
        GuardianRoleEnum types.
        """
        raise NotImplementedError()

    async def _get_user_from_token(self, claims: Dict) -> User:
        """
        This method converts the token obtained from the identity provider to a user object.
        """
        # Verify the content of the given access token
        if "sub" not in claims:
            raise ValueError("Attribute sub not found in provided ADFS claim.")
        elif "firstname" not in claims:
            raise ValueError("Attribute firstname not found in provided ADFS claim.")
        elif "lastname" not in claims:
            raise ValueError("Attribute lastname not found in provided ADFS claim.")
        # Make sure the access token was issued for Guardian
        if claims["client_id"] != settings.client_id:
            raise AuthenticationError("The given claim was not issued for this application.")
        # Extract relevant information from access token and create User object
        email = claims["sub"].lower()
        roles = self._get_roles(claims)
        firstname = claims['firstname']
        lastname = claims['lastname']
        return User(
            email=email,
            roles=roles,
            locked=False,
            full_name=f"{lastname}, {firstname}",
            client_ip=self._client_ip
        )

    async def get_token(self, session: Session):
        access_token = await verify_token(self._token_data["access_token"])
        user = await self._get_user_from_token(access_token)
        token = self.create_token_for_user(session=session, claim_user=user)
        logger.info(f"User {user.email} successfully logged in.")
        return token
