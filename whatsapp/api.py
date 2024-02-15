import asyncio
import json
import logging
import re
from typing import Dict, Optional

from aiohttp import ClientConnectorError, ClientSession, FormData
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
        self.template_path = config["whatsapp.template_path"]
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
        # Set the url to send the message to Whatsapp API
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
        # Set the url to send the interactive message to Whatsapp API
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
        # Set the url to send the read event to Whatsapp API
        mark_read_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        # Set the data to send to Whatsapp API
        data = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
        self.log.debug(f"Marking message as read {data} to {message_id}")

        # Send the read event to the Whatsapp API
        resp = await self.http.post(mark_read_url, data=data, headers=headers)
        response_data = json.loads(await resp.text())

        # If the read event was not sent, raise an error
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
        # Set the url to send the reaction to Whatsapp API
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

    async def send_template(
        self,
        message: str,
        phone_id: WSPhoneID,
        variables: Optional[list] = None,
        template_name: Optional[str] = None,
        media_data: Optional[list] = None,
        language: Optional[str] = "es",
    ) -> Dict:
        """
        It sends a template message to a user.

        Parameters
        ----------
        message: str
            The message of the template.
        phone_id: WSPhoneID
            The id of the whatsapp business phone.
        variables:
            The variables of the template.
        template_name:
            The name of the template.
        media_data: list
            The type and the ids of the media that will be sent to the user.
        language:
            The language of the template.

        Returns
        -------
            A dict with the response of the Whatsapp API.

        """
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }
        # Set the url to send the template to Whatsapp API
        send_template_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/messages"

        self.log.debug(f"Sending template to {send_template_url}")

        parameters = [{"type": "text", "text": value} for value in variables]
        header_parameters = []

        # If the template has a media, add it to the template
        if media_data[0]:
            media_type = media_data[0]
            media_ids = media_data[1]

            header_parameters = [
                {"type": media_type, media_type: {"id": media_id}} for media_id in media_ids
            ]

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_id,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [
                    {"type": "header", "parameters": header_parameters},
                    {"type": "body", "parameters": parameters},
                ],
            },
        }

        self.log.debug(f"Sending template {data} to {phone_id}")

        # Send the template to the Whatsapp API
        resp = await self.http.post(send_template_url, json=data, headers=headers)

        if resp.status not in (200, 201):
            message = await resp.json()
            raise Exception(message.get("error", {}).get("message", ""))

        return await resp.json()

    async def get_template_message(self, template_name: str, variables: Optional[list]) -> tuple:
        """
        Get a template message.

        Parameters
        ----------
        template_name: str
            The name of the template.
        variables: Optional[list]
            The variables of the template.

        Returns
        -------
            A tuple with the message of the template and the status of the template
            (APPROVED, REJECTED, PENDING).
        """
        # Getting the message of the template using the template_name
        # Get the url of the Whatsapp Api Cloud
        url = f"{self.base_url}/{self.version}/{self.business_id}{self.template_path}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }

        params = {
            "name": template_name,
        }

        self.log.debug(f"Getting the approved template from Whatsapp Api Cloud: {url}")
        response: ClientSession = await self.http.get(url=url, headers=headers, params=params)

        if response.status != 200:
            error = await response.json()
            raise Exception(error.get("error", {}).get("message"))

        data = await response.json()
        templates = data.get("data", [])
        template_message = ""
        template_status = ""
        media_data = None
        media_type = ""
        for template in templates:
            # Search the template with the name of the template_name to save it in a text message
            if template.get("name") == template_name:
                for component in template.get("components", []):
                    # If the template has a text, add it to the message, like header, body, footer
                    if component.get("text"):
                        template_message += f"{component.get('text')}\n"
                    # If the template has a button, add it to the message
                    elif component.get("type") == "BUTTONS":
                        for button in component.get("buttons", []):
                            if button.get("type") == "URL":
                                template_message += f"{button.get('text')}: {button.get('url')}\n"
                            elif button.get("type") == "PHONE_NUMBER":
                                template_message += f"{button.get('text')}: {button.get('phone_number').replace('+', '')}\n"
                            else:
                                template_message += f"{button.get('text')}\n"
                    elif component.get("format") in ("IMAGE", "VIDEO", "DOCUMENT"):
                        media_type = component.get("format", "").lower()
                        media_data = [
                            url for url in component.get("example", {}).get("header_handle")
                        ]

                template_status = template.get("status", "")
                self.log.debug(
                    f"""Getting the message of the template: {template_name},
                    status: {template_status}, message: {template_message}"""
                )
                break

        if template_message and variables:
            template_message = re.sub(r"\{\{\d+\}\}", "{}", template_message)
            template_message = template_message.format(*variables)
        return template_message, media_type, media_data, template_status

    async def upload_media(
        self, data_file, messaging_product: str, file_name: str, file_type: str
    ):
        """
        Upload a media to the Whatsap Cloud API.

        Parameters
        ----------
        data_file: File
            The file that will be uploaded.
        messaging_product: str
            The messaging product of the media that whatsapp api will receive.
        file_name: str
            The name of the file.
        file_type: str
            The type of the file.

        Returns
        -------
            The id generated when the media was uploaded.
        """
        form_data = FormData()
        self.log.debug(f"Uploading media to Whatsapp API")
        # Set the headers for the request to the Whatsapp API
        headers = {
            "Authorization": f"Bearer {self.page_access_token}",
        }

        # Set the url to upload the media to Whatsapp API
        upload_media_url = f"{self.base_url}/{self.version}/{self.wb_phone_id}/media"

        # Set the data to send to Whatsapp API
        form_data.add_field("file", data_file, filename=file_name, content_type=file_type)
        form_data.add_field("messaging_product", messaging_product)
        form_data.add_field("type", file_type)

        self.log.debug(f"Uploading media to {upload_media_url}")

        # Send the media to the Whatsapp API
        response: ClientSession = await self.http.post(
            upload_media_url, data=form_data, headers=headers
        )

        # If the media was not sent, return an error
        if response.status not in (200, 201):
            message = await response.json()
            return message

        # Get the id of the media and return it
        data = await response.json()
        return data
