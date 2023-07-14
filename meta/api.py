import asyncio
import json
import logging
from typing import Dict, Optional

from aiohttp import ClientConnectorError, ClientSession
from mautrix.types import MessageEventContent, MessageType

from meta_matrix.config import Config

from .data import MetaUserData
from .types import MetaPsID


class MetaClient:
    log: logging.Logger = logging.getLogger("meta.out")
    http: ClientSession

    def __init__(
        self,
        config: Config,
        loop: asyncio.AbstractEventLoop,
        page_access_token: Optional[str] = None,
        page_id: Optional[str] = None,
    ) -> None:
        self.base_url = config["meta.base_url"]
        self.version = config["meta.version"]
        self.page_access_token = page_access_token
        self.page_id = page_id
        self.http = ClientSession(loop=loop)

    async def get_user_data(self, ps_id: MetaPsID) -> Optional[MetaUserData]:
        params = {
            "field": "fields=first_name,last_name,profile_pic,locale",
            "access_token": self.page_access_token,
        }
        try:
            resp = await self.http.get(f"{self.base_url}/{ps_id}", params=params)
        except ClientConnectorError as e:
            self.log.error(e)
            return None

        response_data = await resp.json()
        return MetaUserData(**response_data)

    async def send_message(
        self,
        matrix_message_evt: MessageEventContent,
        recipient_id: MetaPsID,
    ) -> Dict[str, str]:
        self.log.debug(f"Sending message {matrix_message_evt} to meta user {recipient_id}")

        headers = {"Content-Type": "application/json"}
        send_message_url = (
            f"{self.base_url}/{self.version}/{self.page_id}/"
            f"messages?access_token={self.page_access_token}"
        )

        self.log.debug(f"Sending message to {send_message_url}")

        if matrix_message_evt.msgtype == MessageType.TEXT:
            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": matrix_message_evt.body},
            }
        else:
            self.log.error("Unsupported message type")
            return

        try:
            resp = await self.http.post(send_message_url, json=data, headers=headers)
        except ClientConnectorError as e:
            self.log.error(e)
        response_data = json.loads(await resp.text())
        return response_data
