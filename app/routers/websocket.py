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

import json
import asyncio
import logging
from typing import Annotated, Dict
from core.auth import AuthenticationError
from core.config import settings
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from schema import get_db
from schema.util import ApiPermissionEnum
from schema.user import NotifyUser
from schema.websocket import manager
from schema.database.redis_client import subscribe
from routers.user import verify_token
from sqlalchemy.orm import Session

__author__ = "Lukas Reiter"
__copyright__ = "Copyright (C) 2024 Lukas Reiter"
__license__ = "GPLv3"

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ws",
    tags=["websocket"]
)


async def notify_user_listener():
    """
    Listens to the Redis queue and sends notifications to the users via WebSockets
    """
    try:
        async def send_notification(message: Dict | str):
            try:
                json_object = message if isinstance(message, dict) else json.loads(message)
                notify = NotifyUser(**json_object)
                await manager.send(user=notify.user, status=notify.status)
            except Exception as ex:
                logger.exception(ex)
        await subscribe(
            username=settings.redis_user_notify_user_read,
            password=settings.redis_password_notify_user_read,
            channel=settings.redis_notify_user_channel,
            callback=send_notification
        )
        logger.debug("Redis monitor for WebSocket manager successfully established.")
    except Exception as ex:
        logger.exception(ex)


def start_notify_user_listener():
    """
    Starts the listener for notifying users via WebSockets.
    """
    asyncio.create_task(notify_user_listener())


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    session: Annotated[Session, Depends(get_db)]
):
    """
    Websocket endpoint.
    """
    access_token = websocket.cookies.get("access_token", "")
    x_real_ip = [item.strip() for item in websocket.headers.get("x-real-ip", "").split(",")]
    # 1. We verify the access token and user access
    user, payload = verify_token(session=session, token=access_token, x_real_ip=x_real_ip)
    # 2. We check if the user has the required scopes
    if ApiPermissionEnum.websocket.name not in payload.get("scopes", []):
        logger.critical(f"User {user.email} tried to access scopes {ApiPermissionEnum.websocket.name}.")
        raise AuthenticationError("Could not validate user.")
    await manager.connect(websocket=websocket, user=user)
    # await manager.send(
    #     status=StatusMessage(
    #         status=status.HTTP_200_OK,
    #         message="WebSocket connection established.",
    #         severity=StatusEnum.success
    #     ),
    #     user=user
    # )
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        await manager.disconnect(websocket=websocket, user=user)
