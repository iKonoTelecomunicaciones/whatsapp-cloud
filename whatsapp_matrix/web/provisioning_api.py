from __future__ import annotations

import json
from asyncio import AbstractEventLoop, get_event_loop, sleep
from json import JSONDecodeError
from logging import Logger, getLogger
from urllib.parse import unquote

from aiohttp import ClientResponse, ClientSession, web
from mautrix.types import (
    FileInfo,
    MediaMessageEventContent,
    MessageType,
    TextMessageEventContent,
    UserID,
)

from whatsapp.data import WhatsappContacts
from whatsapp.types import WsBusinessID, WSPhoneID
from whatsapp_matrix.portal import Portal
from whatsapp_matrix.puppet import Puppet

from ..config import Config
from ..db.whatsapp_application import WhatsappApplication
from ..user import User
from ..util import normalize_number


class ProvisioningAPI:
    app: web.Application
    http: ClientSession
    log: Logger = getLogger()

    def __init__(
        self,
        config: Config,
        shared_secret: str,
        loop: AbstractEventLoop = None,
    ) -> None:
        self.loop = loop or get_event_loop()
        self.app = web.Application(loop=self.loop)
        self.shared_secret = shared_secret
        self.base_url = config["whatsapp.base_url"]
        self.version = config["whatsapp.version"]
        self.template_path = config["whatsapp.template_path"]
        self.http = ClientSession(loop=loop)

        self.app.router.add_route("POST", "/v1/register_app", self.register_app)
        self.app.router.add_route("PATCH", "/v1/update_app", self.update_app)
        self.app.router.add_route("GET", "/v1/templates", self.get_template)
        self.app.router.add_route("POST", "/v1/template_approval", self.template_approval)
        self.app.router.add_route("POST", "/v1/pm/{number}", self.start_pm)
        self.app.router.add_route("POST", "/v1/template", self.template)
        self.app.router.add_route("DELETE", "/v1/delete_template", self.delete_template)

    @property
    def _acao_headers(self) -> dict[str, str]:
        """
        Return the Access-Control-Allows headers

        """
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
        }

    @property
    def _headers(self) -> dict[str, str]:
        """
        Return the headers of the request

        """
        return {
            **self._acao_headers,
            "Content-Type": "application/json",
        }

    async def register_app(self, request: web.Request) -> web.Response:
        """
        Register a new Whatsapp app with his matrix user

        Parameters
        ----------
        request : web.Request
            The request that contains the data of the app and the user.

        """
        # Obtain the data from the request
        data = await self._get_body(request)

        try:
            # Separate the data from the request
            app_name = data["app_name"]
            app_business_id = data["app_business_id"]
            app_phone_id = data["app_phone_id"]
            access_token = data["access_token"]
            notice_room = data["notice_room"]
            admin_user = data["admin_user"]
        except KeyError as e:
            raise self._missing_key_error(e)

        # Check if the data does not empty
        if (
            not app_name
            or not app_business_id
            or not access_token
            or not notice_room
            or not admin_user
            or not app_phone_id
        ):
            return web.HTTPBadRequest(
                text=json.dumps({"detail": {"message": "All fields are mandatory"}}),
                headers=self._headers,
            )

        # Check if the business_id and the phone_id are the same
        if app_business_id == app_phone_id:
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {"detail": {"message": "The business_id and the phone_id can not be the same"}}
                ),
                headers=self._headers,
            )

        # Check if the user is already registered. This acd user can be registered because the
        # bridge registers the acd user when it listens that the acd user is invited to the
        # control room
        user: User = await User.get_by_mxid(mxid=admin_user)
        if user.app_business_id:
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {"detail": {"message": "You already have a registered whatsapp_app"}}
                ),
                headers=self._headers,
            )

        # Check if the whatsapp_app is already registered
        if await WhatsappApplication.get_by_business_id(business_id=app_business_id):
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {
                        "detail": {
                            "data": {"businessID": app_business_id},
                            "message": "This app_business_id %(businessID)s is already registered",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the wb_phone_id is already registered
        if await WhatsappApplication.get_by_wb_phone_id(wb_phone_id=app_phone_id):
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {
                        "detail": {
                            "data": {"phoneID": app_phone_id},
                            "message": "The phone_id %(phoneID)s is already registered",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Create the whatsapp_app
        await WhatsappApplication.insert(
            name=app_name,
            admin_user=admin_user,
            business_id=app_business_id,
            wb_phone_id=app_phone_id,
            page_access_token=access_token,
        )

        # Create the user and add the business_id and the notice_room
        user: User = await User.get_by_mxid(mxid=admin_user)
        user.app_business_id = app_business_id
        user.notice_room = notice_room
        await user.update()

        return web.HTTPOk(
            text=json.dumps({"message": "Whatsapp application has been created"}),
            headers=self._headers,
        )

    async def _get_body(self, request: web.Request) -> dict:
        """
        Deserializes the body of the request

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the app and the user.
        """
        self.check_token(request)
        try:
            # Convert the data from the request to json
            data = dict(**await request.json())
        except JSONDecodeError as error:
            self.log.error(f"Malformed JSON {error}")
            raise web.HTTPUnprocessableEntity(
                text=json.dumps({"detail": {"message": f"Malformed JSON {error}"}}),
                headers=self._headers,
            )

        return data

    async def _get_user_and_body(
        self, request: web.Request, read_body: bool = True
    ) -> tuple[User, dict]:
        """
        Get the user and the body of the request

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the app and the user.
        """
        # Validate the token
        self.check_token(request)

        try:
            # Obtain the user_id from the request
            user_id = request.query["user_id"]
        except KeyError:
            raise web.HTTPBadRequest(
                text='{"message": "Missing user_id query param"}', headers=self._headers
            )

        user: User = await User.get_by_mxid(UserID(user_id), create=False)

        if not user:
            raise web.HTTPBadRequest(
                text=json.dumps(
                    {"detail": {"message": f"The user with user_id {user_id} not found"}}
                ),
                headers=self._headers,
            )

        # Obtain the data from the request
        data = await self._get_body(request) if read_body else None
        return user, data

    def _missing_key_error(self, err: KeyError) -> None:
        """
        Return a HTTPBadRequest with the missing key

        Parameters
        ----------
        err : KeyError
            The missing key
        """
        self.log.error(f"KeyError: {err}")
        raise web.HTTPNotAcceptable(
            text=json.dumps(
                {"detail": {"data": {"key": str(err)}, "message": f"Missing key %(key)s"}}
            ),
            headers=self._headers,
        )

    def check_token(self, request: web.Request) -> None:
        """
        Validated that the request has a valid token

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the app and the user.
        """
        try:
            # Obtain the token from the request
            token = request.headers["Authorization"]
            token = token[len("Bearer ") :]
        except KeyError:
            self.log.error("Error getting the Authorization header")
            raise web.HTTPUnauthorized(
                text=json.dumps({"detail": {"message": "Missing Authorization header"}}),
                headers=self._headers,
            )
        # Validate the token
        if token != self.shared_secret:
            raise web.HTTPForbidden(
                text=json.dumps({"detail": {"message": "Invalid token"}}), headers=self._headers
            )

    async def update_app(self, request: web.Request) -> dict:
        """
        Update the Whatsapp_app

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the app and the user.

        Returns
        -------
        JSON
            The response of the request with a success message or an error message
        """
        # Obtain the data from the request
        data = await self._get_body(request)

        if not data:
            return web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "detail": {
                            "message": "The request does not have data",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Separate the data from the request
        app_name = data.get("app_name", None)
        access_token = data.get("access_token", None)
        admin_user = request.query.get("user_id", None)

        if not admin_user:
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {
                        "detail": {
                            "message": "The user was not provided",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the user is registered
        user: User = await User.get_by_mxid(mxid=admin_user, create=False)
        if not user:
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {
                        "detail": {
                            "data": {"username": admin_user},
                            "message": "The user %(username)s is not registered",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the whatsapp_app is registered
        whatsapp_app: WhatsappApplication = await WhatsappApplication.get_by_admin_user(
            admin_user=admin_user
        )

        if not whatsapp_app:
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {
                        "detail": {
                            "data": {"username": admin_user},
                            "message": (
                                "The Whatsapp application with user %(username)s "
                                "is not registered"
                            ),
                        }
                    }
                ),
                headers=self._headers,
            )

        # Update the whatsapp_app with the send values
        data_to_update = (
            app_name if app_name else whatsapp_app.name,
            access_token if access_token else whatsapp_app.page_access_token,
        )

        self.log.debug(f"Update whatsapp_app {whatsapp_app.business_id}")
        await whatsapp_app.update_by_admin_user(
            user=whatsapp_app.admin_user, values=data_to_update
        )

        return web.HTTPOk(
            text=json.dumps(
                {
                    "data": {"businessID": whatsapp_app.business_id},
                    "message": "The whatsapp_app %(businessID)s has been updated",
                }
            ),
            headers=self._headers,
        )

    async def get_template(self, request: web.Request) -> dict:
        """
        Get the template from Whatsapp Api Cloud

        Parameters
        ----------
        business_id: str
            The business_id of the app
        """
        # Validate the token
        self.log.debug("Get template")
        self.check_token(request)

        # Obtain the business_id from the request
        business_id = request.query.get("business_id", None)

        if not business_id:
            self.log.error("The business_id was not provided")
            return web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "detail": {
                            "message": "The request does not have data",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Get the company application and check if the whatsapp_app is registered
        company: WhatsappApplication = await WhatsappApplication.get_by_business_id(
            business_id=business_id
        )

        if not company:
            self.log.error(f"The company application {business_id} is not registered")
            return web.HTTPNotFound(
                text=json.dumps(
                    {
                        "detail": {
                            "data": {"businessID": business_id},
                            "message": "The business_id %(businessID)s is not registered",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Get the url of the Whatsapp Api Cloud
        url = f"{self.base_url}/{self.version}/{business_id}{self.template_path}"
        headers = {
            "Authorization": f"Bearer {company.page_access_token}",
        }

        self.log.debug(f"Getting the template from Whatsapp Api Cloud: {url}")
        client_response: ClientResponse = await self.http.get(url=url, headers=headers)
        response = await client_response.json()
        if client_response.status == 200:
            self.log.debug(f"Get the templates {response}")
            return web.HTTPOk(
                text=json.dumps(response["data"]),
                headers=self._headers,
            )
        else:
            self.log.error(f"Error getting the templates: {response}")
            error = response.get("error", {})
            message_error = (
                error.get("error_user_msg", "")
                if error.get("error_user_msg", "")
                else error.get("message", "")
            )
            self.log.error(f"Error when trying to get the template: {message_error}")
            web.HTTPException.status_code = client_response.status
            return web.HTTPException(
                text=json.dumps(
                    {
                        "detail": {
                            "message": message_error,
                        }
                    }
                ),
                headers=self._headers,
            )

    async def template_approval(self, request: web.Request) -> dict:
        """
        Send a template to approve to Whatsapp Api Cloud

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the app and the user.

        Returns
        -------
        JSON
            The response of the request with a success message or an error message
        """
        self.log.debug("Approval template")
        # Obtain the data from the request
        data = await self._get_body(request)

        if not data:
            return web.HTTPBadRequest(
                text=json.dumps(
                    {
                        "message": "The request does not have data",
                    }
                ),
                headers=self._headers,
            )

        try:
            # Separate the data from the request
            template = json.dumps(data["template"])
            app_business_id = data["app_business_id"]
            app_token = data["app_token"]
        except KeyError as e:
            raise self._missing_key_error(e)

        # Get the url of the Whatsapp Api Cloud
        url = f"{self.base_url}/{self.version}/{app_business_id}{self.template_path}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_token}",
        }
        self.log.debug(f"Sending the approval template to Whatsapp Api Cloud: {url}")
        client_response: ClientResponse = await self.http.post(
            url=url, data=template, headers=headers
        )
        response = await client_response.json()

        if client_response.status in (200, 2001):
            self.log.debug("The template has been sent to approved")
            return web.HTTPOk(
                text=json.dumps(response),
                headers=self._headers,
            )
        else:
            error = response.get("error", {})
            message = (
                error.get("error_user_msg", "")
                if error.get("error_user_msg", "")
                else error.get("message", "")
            )
            self.log.error(f"Error when trying to approve a template: {message}")
            self.log.error(f"Error {response}")
            web.HTTPException.status_code = client_response.status
            return web.HTTPException(
                text=json.dumps(
                    {
                        "message": message,
                    }
                ),
                headers=self._headers,
            )

    async def _get_puppet(self, number: WSPhoneID, app_business_id: WsBusinessID) -> Puppet:
        """
        Obtain the puppet from the number of the user

        Parameters
        ----------
        number: str
            The number of the user

        Returns
        -------
        Puppet
            The puppet of the user
        """
        try:
            number = normalize_number(number).replace("+", "")
        except Exception as e:
            raise web.HTTPBadRequest(text=json.dumps({"error": str(e)}), headers=self._headers)

        puppet: Puppet = await Puppet.get_by_phone_id(
            phone_id=number, app_business_id=app_business_id
        )

        return puppet

    async def start_pm(self, request: web.Request) -> web.Response:
        """
        Created a new room with the user and the puppet to start a new conversation

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the company_app and the user.

        Returns
        -------
        JSON
            The response of the request with the room_id and the chat_id
        """
        self.log.debug("Start PM")
        user, _ = await self._get_user_and_body(request, read_body=False)

        puppet: Puppet = await self._get_puppet(
            number=request.match_info["number"], app_business_id=user.app_business_id
        )
        portal: Portal = await Portal.get_by_app_and_phone_id(
            phone_id=puppet.phone_id, app_business_id=user.app_business_id
        )

        # If the portal is not created, create it
        if portal.mxid:
            await portal.main_intent.invite_user(portal.mxid, user.mxid)
            just_created = False
        else:
            chat_customer = {
                "wa_id": puppet.phone_id,
                "profile": {"name": puppet.display_name or puppet.custom_mxid},
            }
            sender = WhatsappContacts.from_dict(chat_customer)
            await portal.create_matrix_room(user, sender)
            just_created = True

        return web.json_response(
            {
                "room_id": portal.mxid,
            },
            headers=self._acao_headers,
            status=201 if just_created else 200,
        )

    async def template(self, request: web.Request) -> web.Response:
        """
        Send a template to a room

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the company_app and the user.

        Returns
        -------
        JSON
            The response of the request
        """
        self.log.debug("Sending the template")
        media_ids = []
        indexes = []
        user, data = await self._get_user_and_body(request)

        try:
            room_id = data["room_id"]
            template_name = data["template_name"]
            variables = data.get("variables") or []
            language = data.get("language", "es")
            header_variables = data.get("header_variables") or None
            button_variables = data.get("button_variables") or None

        except KeyError as e:
            raise self._missing_key_error(e)

        if variables:
            if type(variables) != list:
                return web.json_response(
                    data={"detail": "variables must be a list"},
                    status=400,
                    headers=self._acao_headers,
                )

        if button_variables:
            if type(button_variables) != list:
                return web.json_response(
                    data={"detail": "button_variables must be a list"},
                    status=400,
                    headers=self._acao_headers,
                )

        if header_variables:
            if type(header_variables) != list:
                return web.json_response(
                    data={"detail": "header_variables must be a list"},
                    status=400,
                    headers=self._acao_headers,
                )

        if not room_id:
            return web.json_response(
                data={"detail": "room_id not entered"},
                status=400,
                headers=self._acao_headers,
            )

        elif not template_name:
            return web.json_response(
                data={"detail": "template_name not entered"},
                status=400,
                headers=self._acao_headers,
            )

        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return web.json_response(
                data={"detail": f"Failed to get room {room_id}"},
                status=400,
                headers=self._acao_headers,
            )

        try:
            (
                template_message,
                media_type,
                media_url,
                template_status,
                indexes,
            ) = await portal.whatsapp_client.get_template_message(
                template_name=template_name,
                body_variables=variables,
                header_variables=header_variables,
                button_variables=button_variables,
            )

        except Exception as e:
            self.log.error(f"Error getting the template message: {e}")
            return web.json_response(
                data={"detail": f"Failed to get template {template_name}: {e}"},
                status=400,
                headers=self._acao_headers,
            )

        if not template_message and not media_type:
            return web.json_response(
                data={"detail": f"The template {template_name} does not exist"},
                status=400,
                headers=self._acao_headers,
            )

        # If the template has media, download it and send it to Matrix
        if media_type and media_url:
            try:
                await self.get_and_send_media(
                    portal=portal, media_type=media_type, media_url=media_url, media_ids=media_ids
                )
            except Exception as e:
                self.log.exception(f"Error trying to send the media message: {e}")
                return web.json_response(
                    data={"detail": f"Error trying to send the media message: {e}"},
                    status=400,
                    headers=self._acao_headers,
                )

        if template_message:
            # Format the message to send to Matrix
            msg = TextMessageEventContent(body=template_message, msgtype=MessageType.TEXT)
            msg.trim_reply_fallback()
            msg_event_id = None
            for i in range(10):
                try:
                    # Send the message to Matrix
                    self.log.debug(f"Trying to send a message to Matrix, attempt: {i + 1}")
                    msg_event_id = await portal.az.intent.send_message(portal.mxid, msg)
                    break

                except Exception as e:
                    self.log.error(f"Error after trying to send the message to Matrix: {e}")
                    await sleep(1)

            if not msg_event_id:
                return web.json_response(
                    data={
                        "detail": f"Failed to send the message to Matrix, please try again later"
                    },
                    status=400,
                    headers=self._acao_headers,
                )

        if template_status == "APPROVED":
            # Send the template to Whatsapp
            status, response = await portal.handle_matrix_template(
                sender=user,
                message=template_message,
                event_id=msg_event_id,
                variables=variables,
                header_variables=header_variables,
                button_variables=button_variables,
                template_name=template_name,
                media=[media_type, media_ids],
                indexes=indexes,
                language=language,
            )
            return web.json_response(data=response, headers=self._acao_headers, status=status)

        else:
            # Send the message to Whatsapp
            await portal.handle_matrix_message(sender=user, message=msg, event_id=msg_event_id)
            return web.json_response(
                data={
                    "detail": f"The template has been sent successfully",
                    "event_id": msg_event_id,
                },
                status=200,
                headers=self._acao_headers,
            )

    async def get_and_send_media(
        self, portal: Portal, media_type: str, media_url: str, media_ids: list
    ) -> None:
        """
        Download the media and send it to Matrix

        Parameters
        ----------
        portal: Portal
            The portal of the room
        media_type: str
            The type of the media
        media_url: str
            The url of the media
        media_ids: list
            The list of the ids of the media that whatsapp cloud api returns
        """
        # Set the message type
        message_type = (
            MessageType.IMAGE
            if media_type == "image"
            else MessageType.VIDEO if media_type == "video" else MessageType.FILE
        )

        for url in media_url:
            # Obtain the media file
            response = await self.http.get(url)
            data = await response.content.read()
            filename = "file"
            file_type = ""
            if "Content-Type" in response.headers:
                file_type = response.headers["Content-Type"]

            # Upload the media to whatsapp cloud api to get the media_id
            response_upload_media = await portal.whatsapp_client.upload_media(
                data_file=data,
                messaging_product="whatsapp",
                file_name=filename,
                file_type=file_type,
            )

            # Check if the media was uploaded or not
            error = response_upload_media.get("error", {}).get("message", "")
            if error:
                return web.json_response(
                    data={"detail": f"Error uploading the media to whatsapp cloud: {error}"},
                    status=400,
                    headers=self._acao_headers,
                )

            # Add the media_id to the list
            media_ids.append(response_upload_media.get("id"))

            try:
                # Upload the message media to Matrix
                attachment = await portal.main_intent.upload_media(data=data)
            except Exception as e:
                self.log.exception(f"Message not receive, error: {e}")
                return web.json_response(
                    data={"detail": "Error trying to upload the media message"},
                    status=400,
                    headers=self._acao_headers,
                )

            # Create the content of the message media for send to Matrix
            content_attachment = MediaMessageEventContent(
                body=filename,
                msgtype=message_type,
                url=attachment,
                info=FileInfo(size=len(data)),
            )

            # Send the message media to Matrix
            await portal.az.intent.send_message(
                room_id=portal.mxid,
                content=content_attachment,
            )

    async def delete_template(self, request: web.Request) -> web.Response:
        """
        delete a template in whatsapp cloud api

        Parameters
        ----------
        request: web.Request
            The request that contains the data of the company_app and the user.

        Returns
        -------
        JSON
            The response of the request
        """
        self.log.debug("Delete template")
        data = await self._get_body(request)

        try:
            app_business_id: WsBusinessID = data["app_business_id"]
            template_name = data["template_name"]
            template_id = data["template_id"]

        except KeyError as e:
            raise self._missing_key_error(e)
        if not template_name or not app_business_id or not template_id:
            return web.json_response(
                data={
                    "message": "The template_name or app_business_id or template_id was not provided"
                },
                status=400,
                headers=self._acao_headers,
            )

        # Get the company application and check if the whatsapp_app is registered
        company: WhatsappApplication = await WhatsappApplication.get_by_business_id(
            business_id=app_business_id
        )

        if not company:
            self.log.error(
                f"The company application with phone {app_business_id} is not registered"
            )
            return web.HTTPNotFound(
                text=json.dumps(
                    {
                        "data": {"app_business_id": app_business_id},
                        "message": "The business_id %(app_business_id)s is not registered",
                    }
                ),
                headers=self._headers,
            )

        # Get the url of the Whatsapp Api Cloud and set the headers
        url = f"{self.base_url}/{self.version}/{app_business_id}{self.template_path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {company.page_access_token}",
        }

        # Set the params of the request
        params = {
            "hsm_id": template_id,
            "name": template_name,
        }

        self.log.debug(f"Sending the delete template to Whatsapp Api Cloud: {url}")
        client_response: ClientResponse = await self.http.delete(
            url=url, params=params, headers=headers
        )
        response = await client_response.json()

        if client_response.status in (200, 2001):
            self.log.debug("The template has been deleted")
            return web.HTTPOk(
                text=json.dumps(response),
                headers=self._headers,
            )
        else:
            error = response.get("error", {})
            message = (
                error.get("error_user_msg", "")
                if error.get("error_user_msg", "")
                else error.get("message", "")
            )
            self.log.error(f"Error when trying to approve a template: {message}")
            self.log.error(f"Error: {response}")
            web.HTTPException.status_code = client_response.status
            return web.HTTPException(
                text=json.dumps(
                    {
                        "message": message,
                    }
                ),
                headers=self._headers,
            )
