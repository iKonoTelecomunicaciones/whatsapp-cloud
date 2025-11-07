import json
import logging
import re
from copy import copy

from aiohttp import ClientConnectorError, ClientSession, FormData
from mautrix.types import MessageType

from whatsapp.data import WhatsappContact, WhatsappMediaData
from whatsapp_matrix.config import Config

from .types import WhatsappMediaID, WhatsappMessageID, WhatsappPhone, WsBusinessID, WSPhoneID
from io import BytesIO


class WhatsappClient:
    log: logging.Logger = logging.getLogger("whatsapp.out")

    def __init__(
        self,
        config: Config,
        session: ClientSession,
        page_access_token: str | None = None,
        business_id: WsBusinessID | None = None,
        wb_phone_id: WSPhoneID | None = None,
    ) -> None:
        self.base_url = config["whatsapp.base_url"]
        self.version = config["whatsapp.version"]
        self.template_path = config["whatsapp.template_path"]
        self.page_access_token = page_access_token
        self.business_id = business_id
        self.wb_phone_id = wb_phone_id
        self.http: ClientSession = session

    async def send_message(
        self,
        phone_id: WhatsappPhone,
        message_type: MessageType,
        message: str | None = None,
        media_id: str | None = None,
        location: tuple | None = None,
        file_name: str | None = None,
        aditional_data: dict | None = None,
    ) -> dict[str, str]:
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

        media_id: str | None
            The media id of the file that will be sent to the user.

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
        match message_type:
            case MessageType.TEXT:
                type_message = "text"
                message_data = {"preview_url": False, "body": message}
            case MessageType.IMAGE:
                type_message = "image"
                message_data = {"id": media_id, "caption": message}
            case MessageType.FILE:
                type_message = "document"
                message_data = {"id": media_id, "filename": file_name, "caption": message}
            case MessageType.VIDEO:
                type_message = "video"
                message_data = {"id": media_id, "caption": message}
            case MessageType.AUDIO:
                type_message = "audio"
                message_data = {"id": media_id}
            case MessageType.LOCATION:
                type_message = "location"
                message_data = {"latitude": location[0], "longitude": location[1]}
            case _:
                self.log.error("Unsupported message type")
                raise TypeError("Unsupported message type")

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
        aditional_data: dict | None = None,
    ) -> dict[str, str]:
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

        self.log.debug(f"Interactive message: {data}")

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
        emoji: str | None = "",
    ) -> dict:
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
        phone_id: WSPhoneID,
        template_data: dict,
        media_data: list | None = None,
    ) -> dict:
        """
        It sends a template message to a user.

        Parameters
        ----------
        phone_id: WSPhoneID
            The id of the whatsapp business phone.
        template_data: dict
            A dict with the information of the template.
        media_data: list
            The type and the ids of the media that will be sent to the user.

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

        header_parameters = []

        # If the template has a media, add it to the template
        if isinstance(media_data, list) and len(media_data) == 2:
            media_type = media_data[0]
            media_ids = media_data[1]

            header_parameters = [
                {"type": media_type, media_type: {"id": media_id}} for media_id in media_ids
            ]

        components = []

        # Set the components of the template ( HEADER, BODY, BUTTONS ) to send it to Whatsapp API
        # Cloud using the standard of the Whatsapp API Cloud.
        if header_parameters:
            components.append({"type": "header", "parameters": header_parameters})

        if template_data.get("header_data"):
            components.append(template_data.get("header_data"))

        if template_data.get("body_data"):
            components.append(template_data.get("body_data"))

        if template_data.get("buttons_data"):
            components.extend(template_data.get("buttons_data"))

        data = {
            "messaging_product": "whatsapp",
            "to": phone_id,
            "type": "template",
            "template": {
                "name": template_data["template_name"],
                "language": {"code": template_data["language"]},
                "components": components,
            },
        }

        self.log.debug(f"Sending template {data} to {phone_id}")

        # Send the template to the Whatsapp API
        resp = await self.http.post(send_template_url, json=data, headers=headers)

        if resp.status not in (200, 201):
            message = await resp.json()
            raise Exception(message.get("error", {}).get("message", ""))

        return await resp.json()

    async def get_template_data(
        self,
        template_name: str,
        variables: list | None,
        language: str,
        parameter_actions: list = [],
    ) -> dict:
        """
        Get a template message.

        Parameters
        ----------
        template_name: str
            The name of the template.
        variables: list[str] | None
            The values of the variables that will be replaced in the message template.
        language: str
            The language of the template
        parameter_actions: list
            Actions that the template needs to be send, usually is used to send flows

        Returns
        -------
            template_data: dict
                A dict with the message of the template, the header, body and footer data,
                the media type and media url if the template has media, the buttons type if
                the template has buttons, the status of the template (APPROVED, REJECTED, PENDING)
                and the language of the template.

                example:
                {
                    "template_name": template_name,
                    "template_to_matrix": [],
                    "media_type": "",
                    "media_url": [],
                    "template_status": "APPROVED",
                    "header_data": {},
                    "body_data": {},
                    "buttons_data": [],
                    "language": "en",
                }
        """
        # Getting the message of the template using the template_name
        # Get the url of the Whatsapp Api Cloud
        url = f"{self.base_url}/{self.version}/{self.business_id}{self.template_path}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.page_access_token}",
        }

        params = {"name": template_name}

        self.log.debug(f"Getting the approved template from Whatsapp Api Cloud: {url}")
        response: ClientSession = await self.http.get(url=url, headers=headers, params=params)

        if response.status != 200:
            error = await response.json()
            raise Exception(error.get("error", {}).get("message"))

        data = await response.json()
        templates = data.get("data", [])

        return self.search_and_get_template_message(
            templates=templates,
            template_name=template_name,
            variables=variables,
            language=language,
            parameter_actions=parameter_actions,
        )

    async def upload_media(
        self, data_file, messaging_product: str, file_name: str, file_type: str
    ):
        """
        Upload a media to the Whatsapp Cloud API.

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

        data = await response.json()
        return data

    def get_header_component(
        self, component: dict, variables: list[str] | None, template_data: dict
    ):
        """
        Get the message of the header and validate if the header has a media to save the type and
        the url of it.

        Parameters
        ----------
        component: dict
            The component of the template.
        variables: list[str] | None
            The values of the variables that will be replaced in the message template.
        template_data: dict
            The data of the template.
        """
        # Get the message of the header
        self.get_message_component(
            component=component, variables=variables, template_data=template_data
        )

        # If the header has a media, get the type and the url of the media
        if component.get("format") in ("IMAGE", "VIDEO", "DOCUMENT"):
            template_data["media_type"] = component.get("format", "").lower()
            # The media url is saved in the example of the template, usually in the header_handle
            # that is a list with the url of the media.
            template_data["media_url"] = component.get("example", {}).get("header_handle")

    def get_template_variables(
        self,
        component: dict,
        template_data: dict,
        message_variables: list[str],
        variables: list[str],
    ):
        """
        Get the variables of the template message, replace the values of the variables in the
        message template and save the variables to send it to Whatsapp API Cloud.

        Parameters
        ----------
        component: dict
            The component of the template.
        template_data: dict
            The data of the template.
        message_variables: list[str]
            The variables that the message template contains.
        variables: list[str]
            The values of the variables that will be replaced in the message template.
        """
        total_message_variables = len(message_variables)
        # Get the component type ( HEADER, BODY, FOOTER )
        component_type = component.get("type").lower()
        component_type_data = f"{component_type}_data"
        # Replace the variables standar of Meta Template ( {{name}}, {{1}} ) with
        # our standar ( {} ), this is because the variables of the template are in a list and we
        # need to replace it in the message.
        message = re.sub(r"{{[a-z0-9_]+}}", "{}", component.get("text"))
        # component_example contains the example of the component, when the component has named
        # variables, it contains the name of the variables and other information of the message.
        component_example = component.get("example", {})
        # named_params contains the name of the variables of the template
        named_params = component_example.get(f"{component_type}_text_named_params")

        # If the template has variables, replace the variable and add it to the message
        replaced_component = copy(component)
        try:
            replaced_component["text"] = message.format(*variables[:total_message_variables])
        except KeyError:
            pass

        template_data["template_to_matrix"].append(replaced_component)

        # Save the variables of the template to send it to Whatsapp API Cloud
        parameters_data = [
            {"type": "text", "text": variable} for variable in variables[:total_message_variables]
        ]

        # Remove the variables of the template that were replaced
        del variables[:total_message_variables]

        # If the variables have a name ( like {{name}} ), add it to the variable
        # This is used to send the names of the variables to Whatsapp API Cloud
        if component_example and named_params:
            for index, param in enumerate(named_params):
                parameters_data[index]["parameter_name"] = param.get("param_name")

        # Save the format of the component and the parameters of the template
        template_data[component_type_data] = {
            "type": component_type,
            "parameters": parameters_data,
        }

    def get_message_component(
        self, component: dict, variables: list[str] | None, template_data: dict
    ):
        """
        Get the message of a component type (HEADER, BODY, FOOTER) and validate if the component
        has variables, if the component has variables, replace the variables, add it to
        the message and save the variables of the template to send it to Whatsapp API Cloud.

        Parameters
        ----------
        component: dict
            The component of the template.
        variables: list[str] | None
            The values of the variables that will be replaced in the message template.
        template_data: dict
            The data of the template.
        """
        # Get the variables of the template message, each variable is in the format {{name}} or
        # {{1}}
        message_variables = re.findall(r"{{[a-z0-9_]+}}", component.get("text", ""))

        if not variables and message_variables:
            raise ValueError(
                "the template has body with variables, but the variables are not provided"
            )

        if template_data.get("template_to_matrix") is None:
            template_data["template_to_matrix"] = []

        # If the template has variables, replace the variable and add it to the message
        if message_variables:
            self.get_template_variables(
                template_data=template_data,
                component=component,
                message_variables=message_variables,
                variables=variables,
            )
        else:
            template_data["template_to_matrix"].append(component)

    def get_button_url(self, button: dict, variables: list[str]) -> dict[str, str] | None:
        """
        Validate if the button has a variable, if it has, replace the variable and add it to the
        parameter dictionary, else add the url of the button to the message.

        Parameters
        ----------
        button: dict
            The button of the template.
        variables: list[str]
            The values of the variables that will be replaced in the button message.
        """
        # Get the variables of the template message, each variable is in the format {{1}}
        has_button_variables = re.findall(r"\{\{\d+\}\}", button.get("url", ""))

        if not variables and has_button_variables:
            raise ValueError(
                "The template has button with variable, but the variable are not provided"
            )

        # The parameter is not set by default because if the button has not a variable, the
        # parameter is not needed
        parameter = None

        if has_button_variables:
            variable = variables.pop(0)
            # Replace the variables standar of Meta Template ( {{name}}, {{1}} ) with our standar
            # ( {} ), this is because the variables of the template are in a list and we need to
            # replace it in the message.
            parameter = {"type": "text", "text": variable}

        return parameter

    def get_buttons_component(
        self,
        component: dict,
        variables: list[str] | None,
        template_data: dict,
        parameter_actions: list,
    ):
        """
        Get the buttons of the template and validate the type of the button to send it to Whatsapp
        API Cloud, if the button has a url, validate if it has a variable or not, also validate
        others types of buttons to send the valid parameters that Whatsapp API Cloud needs.

        Parameters
        ----------
        component: dict
            The component of the template.
        variables: list[str] | None
            The values of the variables that will be replaced in the message template.
        template_data: dict
            The data of the template.
        parameter_actions: list
            Actions that the template needs to be send, usually is used to send flows
        """
        # Append the button to the template matrix
        template_data["template_to_matrix"].append(
            {"type": "BUTTONS", "buttons": component.get("buttons", [])}
        )

        for i, button in enumerate(component.get("buttons", [])):
            # Get the type of the button and its text
            button_type = button.get("type", "").lower()
            # Set the default parameters of the button
            parameter: dict = {"type": "text", "text": button.get("text")}

            match button_type:
                case "quick_reply":
                    parameter = {"type": "payload", "payload": button.get("text")}

                case "flow":
                    parameter = {"type": "action", "action": {}}
                    parameter = {
                        "type": "action",
                        "action": {
                            "flow_action_data": (
                                parameter_actions.pop() if len(parameter_actions) > 0 else {}
                            )
                        },
                    }

                case "catalog":
                    parameter = {"type": "action", "action": {}}

                # If the template has a url button, validate if the button has a variable or not
                case "url":
                    parameter = self.get_button_url(
                        button=button,
                        variables=variables,
                    )

                # If the template has a button with a number, add it to the message
                case "phone_number":
                    button_type = "voice_call"
                    parameter = {
                        "type": "text",
                        "text": button.get("phone_number", ""),
                    }

                # If the template has a button with a coupon code, add it to the message
                case "copy_code":
                    button_type = button.get("type", "")
                    variable = variables.pop(0) if variables else ""
                    parameter = {
                        "type": "coupon_code",
                        "coupon_code": variable,
                    }

            if not parameter:
                continue

            # If the button has a parameter, add it to the button
            template_data["buttons_data"].append(
                {
                    "type": "button",
                    "sub_type": button_type,
                    "index": i,
                    "parameters": [parameter],
                }
            )

    def get_component_data(
        self,
        component: dict,
        template_data: dict,
        template_variables: list[str],
        parameter_actions: list,
    ):
        """
        Validate the type of the component (HEADER, BODY, FOOTER, BUTTONS) and get the relevant
        information of the component.

        Parameters
        ----------
        component: dict
            The component of the template.
        template_data: dict
            The data of the template.
        template_variables: list[str]
            The values of the variables that will be replaced in the message template.
        parameter_actions: list
            Actions that the template needs to be send, usually is used to send flows
        """
        match component.get("type"):
            case "HEADER":
                self.get_header_component(
                    component=component,
                    variables=template_variables,
                    template_data=template_data,
                )
            case "BODY" | "FOOTER":
                self.get_message_component(
                    component=component,
                    variables=template_variables,
                    template_data=template_data,
                )
            case "BUTTONS":
                self.get_buttons_component(
                    component=component,
                    variables=template_variables,
                    template_data=template_data,
                    parameter_actions=parameter_actions,
                )

    def search_and_get_template_message(
        self,
        templates: list[dict],
        template_name: str,
        language: str,
        variables: list[str] | None = [],
        parameter_actions: list = [],
    ) -> dict:
        """
        Search the template in a list of templates and return a dict with the relevant information
        of the template.

        Parameters
        ----------
        templates: list
            The list of templates.
        template_name: str
            The name of the template that will be search.
        language: str
            The language of the template.
        variables: list[str] | None
            The values of the variables that will be replaced in the template.
        parameter_actions: list
            Actions that the template needs to be send, usually is used to send flows

        Returns
        -------
            template_data: dict
                A dict with the message of the template, the header, body and footer data,
                the media type and media url if the template has media, the buttons type if
                the template has buttons, the status of the template (APPROVED, REJECTED, PENDING)
                and the language of the template.

                example:
                {
                    "template_name": template_name,
                    "template_to_matrix": [],
                    "media_type": "",
                    "media_url": [],
                    "template_status": "APPROVED",
                    "header_data": {},
                    "body_data": {},
                    "buttons_data": [],
                    "language": "en",
                }
        """
        # Template data has the relevant information of the template, like the message,
        # the language, the media type, the media url, the status of the template, the header data,
        # body data, and buttons data
        template_data = {
            "template_name": template_name,
            "template_to_matrix": [],
            "media_type": "",
            "media_url": [],
            "template_status": "",
            "header_data": {},
            "body_data": {},
            "buttons_data": [],
            "language": language,
        }

        template = None
        template_variables = copy(variables)

        for facebook_template in templates:
            if facebook_template.get("name") == template_name:
                template = facebook_template
                break

        if not template:
            self.log.error(f"Template {template_name} not found")
            raise ValueError(f"The template {template_name} does not exist")

        # Search the template with the name of the template_name to save it in a text message
        template_data["template_status"] = template.get("status", "")

        # Iterate over the components of the template to get the relevant information of the
        # template
        for component in template.get("components", []):
            self.get_component_data(
                component, template_data, template_variables, parameter_actions
            )

        self.log.debug(
            f"""
            Getting the message of the template: {template_name},
            status: {template_data['template_status']},
            message: {template_data['template_to_matrix']}
            """
        )

        return template_data

    def generate_vcard(self, contacts: list[WhatsappContact]) -> tuple[str, bytes]:
        """
        Generate a vCard from a list of WhatsappContact.

        Parameters
        ----------
        contacts: list[WhatsappContact]
            A list of WhatsappContact.

        Returns
        -------
            A tuple with the filename and the vCard in bytes.
        """

        vcard_str = "BEGIN:VCARD\nVERSION:3.0\n"
        file_name = "contacts.vcf"

        if len(contacts) == 1:
            file_name = f"{contacts[0].name.formatted_name}.vcf"

        for contact in contacts:
            full_name = contact.name.formatted_name or ""
            name = (
                f"{contact.name.last_name};{contact.name.first_name};"
                f"{contact.name.middle_name};;{contact.name.suffix}"
            )
            vcard_str += f"N:{name}\n"
            vcard_str += f"FN:{full_name}\n"

            if contact.org.company:
                vcard_str += f"ORG:{contact.org.company}\n"
                vcard_str += f"TITLE:{contact.org.title}\n"

            for data in contact.emails:
                vcard_str += f"EMAIL;TYPE={data.type.capitalize()}:{data.email}\n"

            for phone in contact.phones:
                phone_type = phone.type.upper() if phone.type else "Mobile"
                vcard_str += f'TEL;TYPE={phone_type};waid={phone.wa_id}:{phone.phone}\n'

            for url in contact.urls:
                vcard_str += f'URL;TYPE={url.type}:{url.url}\n'

            for address in contact.addresses:
                vcard_str += f"ADR;TYPE={address.type}:;;{address.street};;;;\n"

            if contact.birthday:
                vcard_str += f"BDAY;value=date:{contact.birthday}\n"

        vcard_str += "END:VCARD\n"

        # Simulate writing to a file in memory and return the bytes
        vcard_bytes = vcard_str.encode("utf-8")
        buffer = BytesIO()
        buffer.write(vcard_bytes)
        buffer.seek(0)
        return file_name, buffer.getvalue()