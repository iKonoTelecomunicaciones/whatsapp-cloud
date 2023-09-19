import asyncio
import json
import logging
from typing import Dict, Optional

from aiohttp import ClientConnectorError, ClientSession
from mautrix.types import MessageType

from whatsapp_matrix.config import Config

from .types import WhatsappPhone, WsBusinessID, WSPhoneID


class WhatsappClient:
    log: logging.Logger = logging.getLogger("whatsapp.out")
    http: ClientSession

    def __init__(
        self,
        config: Config,
        loop: asyncio.AbstractEventLoop,
        page_access_token: Optional[str] = None,
        business_id: Optional[WsBusinessID] = None,
        ws_phone_id: Optional[WSPhoneID] = None,
    ) -> None:
        self.base_url = config["whatsapp.base_url"]
        self.version = config["whatsapp.version"]
        self.page_access_token = page_access_token
        self.business_id = business_id
        self.ws_phone_id = ws_phone_id
        self.http = ClientSession(loop=loop)

    async def send_message(
        self,
        message: str,
        phone_id: WhatsappPhone,
        message_type: MessageType,
    ) -> Dict[str, str]:
        """
        Send a message to the user.

        Parameters
        ----------
        message : str
            The message that will be send to the user.

        phone_id : WhatsappPhone
            The number of the user.

        message_type: MessageType
            The type of the message that will be send to the user.
        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the message to Wahtsapp API
        send_message_url = f"{self.base_url}/{self.version}/{self.ws_phone_id}/messages"

        self.log.debug(f"Sending message to {send_message_url}")

        # Set the data to send to Whatsapp API
        if message_type == MessageType.TEXT:
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_id,
                "type": "text",
                "text": {"preview_url": False, "body": message},
            }

        else:
            self.log.error("Unsupported message type")
            return

        self.log.debug(f"Sending message {data} to {phone_id}")

        try:
            # Send the message to the Whatsapp API
            resp = await self.http.post(send_message_url, json=data, headers=headers)
        except ClientConnectorError as e:
            self.log.error(e)
            return

        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise FileNotFoundError(response_data)

        return response_data
