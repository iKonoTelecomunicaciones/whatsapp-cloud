import asyncio
import json
import logging
from typing import Dict, Optional

from aiohttp import ClientConnectorError, ClientSession
from mautrix.types import MessageType

from meta_matrix.config import Config

from .data import FacebookUserData, InstagramUserData
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

    async def get_user_data(
        self, ps_id: MetaPsID
    ) -> Optional[FacebookUserData] | Optional[InstagramUserData]:
        params = {
            "field": "fields=first_name,last_name,profile_pic,locale",
            "access_token": self.page_access_token,
        }
        try:
            resp = await self.http.get(f"{self.base_url}/{ps_id}", params=params)
        except ClientConnectorError as e:
            self.log.error(e)
            return None

        self.log.debug(f"Getting user data from {await resp.json()}")

        response_data = await resp.json()

        try:
            user_data = FacebookUserData(**response_data)
        except TypeError:
            user_data = InstagramUserData(**response_data)

        return user_data

    async def send_message(
        self,
        message: str,
        recipient_id: MetaPsID,
        message_type: MessageType,
        aditional_data: Optional[Dict] = None,
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        send_message_url = (
            f"{self.base_url}/{self.version}/{self.page_id}/"
            f"messages?access_token={self.page_access_token}"
        )

        self.log.debug(f"Sending message to {send_message_url}")

        if message_type == MessageType.TEXT:
            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": message},
            }
            if aditional_data.get("reply_to"):
                data["message_id"] = {"mid": aditional_data["reply_to"]["mid"]}

        # Send the media message to the Meta API
        elif (
            message_type == MessageType.IMAGE
            or message_type == MessageType.VIDEO
            or message_type == MessageType.AUDIO
            or message_type == MessageType.FILE
        ):
            message_type = (
                "image"
                if message_type == MessageType.IMAGE
                else "video"
                if message_type == MessageType.VIDEO
                else "audio"
                if message_type == MessageType.AUDIO
                else "file"
                if message_type == MessageType.FILE
                else None
            )

            # Fit the necessary data for the Meta API
            data = {
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {"type": message_type, "payload": {"url": url}},
                },
            }

            # If the message is a reply, add the message_id
            if aditional_data.get("reply_to"):
                data["message_id"] = {"mid": aditional_data["reply_to"]["mid"]}
        elif message_type == "m.interactive_message":
            data = {
                "recipient": {"id": recipient_id},
                "messaging_type": "RESPONSE",
            }

            if not aditional_data.get("type", None):
                data["message"] = aditional_data
            elif aditional_data.get("type") == "template":
                data.update({"message": {"attachment": aditional_data}})
        else:
            self.log.error("Unsupported message type")
            return

        self.log.debug(f"Sending message {data} to {recipient_id}")

        try:
            # Send the message to the Meta API
            resp = await self.http.post(send_message_url, json=data, headers=headers)
        except ClientConnectorError as e:
            self.log.error(e)

        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise FileNotFoundError(response_data)

        return response_data

    async def send_read_receipt(self, recipient_id: MetaPsID) -> None:
        headers = {"Content-Type": "application/json"}
        mark_message_as_read_url = (
            f"{self.base_url}/{self.version}/me/messages?access_token={self.page_access_token}"
        )

        data = {"recipient": {"id": recipient_id}, "sender_action": "mark_seen"}

        try:
            await self.http.post(mark_message_as_read_url, json=data, headers=headers)
        except ClientConnectorError as e:
            self.log.error(e)
