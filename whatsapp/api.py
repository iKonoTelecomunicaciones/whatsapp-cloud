import asyncio
import json
import logging
from typing import Dict, Optional

from aiohttp import ClientConnectorError, ClientSession
from mautrix.types import MessageType

from whatsapp.data import WhatsappMediaData
from whatsapp_matrix.config import Config

from .types import WhatsappMediaID, WhatsappMessageID, WhatsappPhone, WsBusinessID, WSPhoneID


class WhatsappClient:
    log: logging.Logger = logging.getLogger("whatsapp.out")
    http: ClientSession

    def __init__(
        self,
        config: Config,
        loop: asyncio.AbstractEventLoop,
        page_access_token: Optional[str] = None,
        business_id: Optional[WsBusinessID] = None,
        wb_phone_id: Optional[WSPhoneID] = None,
    ) -> None:
        self.base_url = config["whatsapp.base_url"]
        self.version = config["whatsapp.version"]
        self.page_access_token = page_access_token
        self.business_id = business_id
        self.wb_phone_id = wb_phone_id
        self.http = ClientSession(loop=loop)

    async def send_message(
        self,
        phone_id: WhatsappPhone,
        message_type: MessageType,
        message: Optional[str] = None,
        url: Optional[str] = None,
        location: Optional[tuple] = None,
        aditional_data: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """
        Send a message to the user.

        Parameters
        ----------
        message : str
            The message that will be sent to the user.

        phone_id : WhatsappPhone
            The number of the user.

        message_type: MessageType
            The type of the message that will be sent to the user.

        url: str
            The url of the file that will be sent to the user.

        location: tuple
            The location of the user, contains the latitude and longitude.

        aditional_data: dict
            This is used to send a reply to a message.

        Exceptions
        ----------
        TypeError:
            If the message type is not supported.
        ValueError:
            If the message was not sent.
        ClientConnectorError:
            If the connection to the Whatsapp API fails.

        Returns
        -------
        Return the response of the Whatsapp API.
        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the message to Wahtsapp API
        send_message_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        self.log.debug(f"Sending message to {send_message_url}")

        # Set the data to send to Whatsapp API
        type_message = (
            "text"
            if message_type == MessageType.TEXT
            else "image"
            if message_type == MessageType.IMAGE
            else "video"
            if message_type == MessageType.VIDEO
            else "audio"
            if message_type == MessageType.AUDIO
            else "document"
            if message_type == MessageType.FILE
            else "location"
            if message_type == MessageType.LOCATION
            else None
        )

        if not type_message:
            self.log.error("Unsupported message type")
            raise TypeError("Unsupported message type")

        message_data = (
            {"preview_url": False, "body": message}
            if message_type == MessageType.TEXT
            else {"link": url, "filename": "File"}
            if message_type == MessageType.FILE
            else {"latitude": location[0], "longitude": location[1]}
            if message_type == MessageType.LOCATION
            else {"link": url}
        )

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_id,
            "type": type_message,
            type_message: message_data,
        }

        # If the message is a reply, add the message_id
        if aditional_data.get("reply_to"):
            data["context"] = {"message_id": aditional_data["reply_to"]["wb_message_id"]}
        self.log.debug(f"Sending message {data} to {phone_id}")

        # Send the message to the Whatsapp API
        resp = await self.http.post(send_message_url, json=data, headers=headers)
        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise ValueError(response_data)

        return response_data

    async def send_interactive_message(
        self,
        phone_id: WhatsappPhone,
        message_type: MessageType,
        aditional_data: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """
        Send an interactive message to the user.

        Parameters
        ----------
        phone_id : WhatsappPhone
            The number of the user.

        message_type: MessageType
            The type of the message that will be sent to the user.

        aditional_data:
            The data of the interactive message that will be sent to the user.

        Exceptions
        ----------
        TypeError:
            If the message type is not supported.
        ValueError:
            If the message was not sent.
        AttributeError:
            If the atributes of the message are not correct.
        FileNotFoundError:
            If the atrributes of the message has not a file required.
        ClientConnectorError:
            If the connection to the Whatsapp API fails.

        Returns
        -------
        Return the response of the Whatsapp API.
        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the message to Wahtsapp API
        send_message_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        self.log.debug(f"Sending interactive message to {send_message_url}")

        # Set the data to send to Whatsapp API
        type_message = "interactive" if message_type == "m.interactive_message" else None

        if not type_message:
            self.log.error("Unsupported message type")
            raise TypeError("Unsupported message type")

        message_data = aditional_data
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_id,
            "type": type_message,
            type_message: message_data,
        }

        # Send the message to the Whatsapp API
        resp = await self.http.post(send_message_url, json=data, headers=headers)
        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise ValueError(response_data)

        return response_data

    async def get_media(self, media_id: WhatsappMediaID):
        """
        Get the url of the media and with it, search the media in the Whatsapp API.

        Parameters
        ----------
        media_id : str
            The id of the media.

        Exceptions
        ----------
        ClientConnectorError:
            If the connection to the Whatsapp API fails.

        Returns
        -------
        File:
            The media that was searched.
        """
        params = {
            "access_token": self.page_access_token,
        }
        headers = {
            "Authorization": f"Bearer {self.page_access_token}",
        }

        try:
            resp = await self.http.get(f"{self.base_url}/{media_id}", params=params)
        except ClientConnectorError as e:
            self.log.error(e)
            return None

        self.log.debug(f"Getting data of media from {await resp.json()}")
        data = await resp.json()

        if data.get("error", {}):
            self.log.error(f"Error getting the data of the media: {data.get('error')}")
            return None

        media_data = WhatsappMediaData.from_dict(data)

        try:
            media = await self.http.get(f"{media_data.url}", headers=headers)
        except ClientConnectorError as e:
            self.log.error(e)
            return None

        return media

    async def mark_read(self, message_id: WhatsappMessageID):
        """
        Mark the message as read.

        Parameters
        ----------
        message_id : str
            The id of the message.

        Exceptions
        ----------
        AttributeError:
            If the message was not sent.

        Returns
        -------
        Return the response of the Whatsapp API.
        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the message to Wahtsapp API
        mark_read_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        # Set the data to send to Whatsapp API
        data = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
        self.log.debug(f"Marking message as read {data} to {message_id}")

        # Send the message to the Whatsapp API
        resp = await self.http.post(mark_read_url, data=data, headers=headers)
        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise AttributeError(response_data)

        return response_data

    async def send_reaction(
        self,
        message_id: WhatsappMessageID,
        phone_id: WSPhoneID,
        emoji: Optional[str] = "",
    ) -> Dict:
        """
        Send a reaction to the user.

        Parameters
        ----------
        message_id : str
            The id of the message that will been reacted.

        phone_id : WhatsappPhone
            The number of the user.

        emoji: str
            The emoji that will be sent to the user.

        Returns
        -------
        Return the response of the Whatsapp API.
        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the message to Wahtsapp API
        send_message_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        self.log.debug(f"Sending message to {send_message_url}")

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_id,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }

        self.log.debug(f"Sending reaction {data} to {phone_id}")

        # Send the reaction to the Whatsapp API
        resp = await self.http.post(send_message_url, json=data, headers=headers)
        response_data = json.loads(await resp.text())

        # If the message was not sent, raise an error
        if response_data.get("error", {}):
            raise FileNotFoundError(response_data)

        return response_data
