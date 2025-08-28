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

from httpx import Response
from core.config import IdentityProviderType
from . import IdentityProviderBase
from .adfs import AdfsIdentityProvider
from .keycloak import KeycloakIdentityProvider

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"


class IdentityProviderFactory:
    """
    Singleton that returns the correct identity provider.
    """
    def __init__(self):
        raise NotImplementedError()

    @staticmethod
    def get(
            idp_type: IdentityProviderType,
            client_ip: str | None,
            response: Response
    ) -> IdentityProviderBase:
        if idp_type == IdentityProviderType.adfs:
            return AdfsIdentityProvider(response=response, client_ip=client_ip)
        elif idp_type == IdentityProviderType.keycloak:
            return KeycloakIdentityProvider(response=response, client_ip=client_ip)
        else:
            raise ValueError(f"Provider type '{idp_type.name}' is unknown.")
