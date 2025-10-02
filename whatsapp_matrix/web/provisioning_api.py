from __future__ import annotations

import json
from asyncio import AbstractEventLoop, get_event_loop
from json import JSONDecodeError
from logging import Logger, getLogger
import stat

from aiohttp import ClientResponse, ClientSession, web
from mautrix.types import UserID

from whatsapp.data import WhatsappContacts
from whatsapp.types import WsBusinessID, WSPhoneID
from whatsapp_matrix import user
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
        self.app.router.add_route("POST", "/v1/set_power_level", self.set_power_level)
        self.app.router.add_route("POST", "/v1/set_relay", self.set_relay)
        self.app.router.add_route("GET", "/v1/set_relay/{room_id}", self.validate_set_relay)

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

        page: str
            The page of the template to get
        """
        # Validate the token
        self.log.debug("Get template")
        self.check_token(request)

        # Obtain the business_id from the request
        business_id = request.query.get("business_id")
        # Obtain the page from the request
        page = request.query.get("page")

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
        url = f"{self.base_url}/{self.version}/{business_id}{self.template_path}?limit=50"

        if page:
            url += f"&after={page}"

        headers = {
            "Authorization": f"Bearer {company.page_access_token}",
        }

        self.log.debug(f"Getting the template from Whatsapp Api Cloud: {url}")
        client_response: ClientResponse = await self.http.get(url=url, headers=headers)
        response = await client_response.json()
        if client_response.status == 200:
            self.log.debug(f"Get the templates {response}")
            return web.HTTPOk(
                text=json.dumps(response),
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
            The request that contains the data of:

            - room_id: str
                The room_id of the room
            - template_name: str
                The name of the template
            - variables: list
                The values of the variables of the template that Whatsapp Api Cloud needs
            - language: str
                The language of the template
            - header_variables: Optional[list] (deprecated)
                The values of the variables of the header of the template that Whatsapp Api Cloud
                needs
            - button_variables: Optional[list] (deprecated)
                The values of the variables of the buttons of the template that Whatsapp Api Cloud
                needs
            - flow_action: JSON | None
                The content action of the flow, if the template is a flow template and the flow
                has dynamic values

        Returns
        -------
        JSON
            The response of the request
        """
        self.log.debug("Sending the template")
        user, data = await self._get_user_and_body(request)

        try:
            room_id = data["room_id"]
            template_name = data["template_name"]
            variables = data.get("variables") or []
            language = data.get("language", "es")
            header_variables = data.get("header_variables") or None
            button_variables = data.get("button_variables") or None
            flow_action = data.get("flow_action") or None

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

            variables = [*variables, *button_variables]

        if header_variables:
            if type(header_variables) != list:
                return web.json_response(
                    data={"detail": "header_variables must be a list"},
                    status=400,
                    headers=self._acao_headers,
                )

            variables = [*header_variables, *variables]

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
            # Send the template or message (depend if the template are approved or not) to the room
            status, response = await portal.validate_and_send_template(
                template_name=template_name,
                variables=variables,
                flow_action=flow_action,
                language=language,
                user=user,
            )

            return web.json_response(data=response, headers=self._acao_headers, status=status)
        except ValueError as e:
            return web.json_response(
                data={"detail": str(e)},
                status=400,
                headers=self._acao_headers,
            )
        except IndexError as e:
            self.log.error(f"Error replacing the variables: {e}")
            return web.json_response(
                data={"detail": f"Error replacing the variables, maybe some variable is missing"},
                status=400,
                headers=self._acao_headers,
            )
        except Exception as e:
            self.log.error(f"Error getting the template message: {e}")
            return web.json_response(
                data={"detail": f"Failed to get template {template_name}: {e}"},
                status=400,
                headers=self._acao_headers,
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

    async def set_power_level(self, request: web.Request) -> web.Response:
        """
        Set the power level of a user in a room
        Parameters
        ----------
        request: web.Request
            The request that contains the data of the company_app and the user.
        Returns
        -------
        JSON
            The response of the request with a success message or an error message
        """
        data = await self._get_body(request)

        try:
            user_id = data["user_id"]
            power_level = data["power_level"]
            room_id = data["room_id"]
        except KeyError as e:
            raise self._missing_key_error(e)

        self.log.debug(
            f"Set power level for room {room_id} and user {user_id} with power level {power_level}"
        )

        if not user_id or power_level is None or power_level < 0 or not room_id:
            return web.json_response(
                data={
                    "detail": {"message": "The user_id or power_level or room_id was not provided"}
                },
                status=400,
                headers=self._acao_headers,
            )

        # Get the portal by room_id
        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return web.json_response(
                data={"detail": {"message": f"Failed to get portal {room_id}"}},
                status=400,
                headers=self._acao_headers,
            )
        # Get the power level of the room
        try:
            power_levels = await portal.main_intent.get_power_levels(room_id)
        except Exception as e:
            self.log.error(f"Error getting the power level: {e}")
            return web.json_response(
                data={
                    "detail": {
                        "message": f"Failed to get power level for room {room_id}. Error:{e}"
                    }
                },
                status=400,
                headers=self._acao_headers,
            )

        # Change the power level of the user
        power_levels.set_user_level(user_id, power_level)

        # Update the power level of the user in the room
        try:
            await portal.main_intent.set_power_levels(
                room_id=room_id,
                content=power_levels,
            )
        except Exception as e:
            self.log.error(f"Error setting the power level for portal {room_id}. Error: {e}")
            return web.json_response(
                data={
                    "detail": {
                        "message": f"Failed to set power level for user {user_id} in portal {room_id}. Error:{e}"
                    }
                },
                status=400,
                headers=self._acao_headers,
            )

        self.log.debug(f"Set power level for user {user_id} in portal {room_id}")
        return web.json_response(
            data={
                "detail": {
                    "message": f"Set power level for user {user_id} in portal {room_id} with power level {power_level} was successful"
                }
            },
            status=200,
            headers=self._acao_headers,
        )

    async def set_relay(self, request: web.Request) -> web.Response:
        """
        Set the relay of a user in a room
        Parameters
        ----------
        request: web.Request
            The request that contains the data of the company_app and the user.
        Returns
        -------
        JSON
            The response of the request with a success message or an error message
        """
        data = await self._get_body(request)

        try:
            room_id = data["room_id"]
        except KeyError as e:
            raise self._missing_key_error(e)

        self.log.debug(f"Set relay for room {room_id}")
        if not room_id:
            self.log.error("The room_id was not provided")
            return web.json_response(
                data={"detail": {"message": "The room_id was not provided"}},
                status=400,
                headers=self._acao_headers,
            )

        # Get the portal by room_id
        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            self.log.error(f"Portal {room_id} not found")
            return web.json_response(
                data={"detail": {"message": f"Failed to get portal {room_id}"}},
                status=400,
                headers=self._acao_headers,
            )

        user: User = await User.get_by_mxid(portal.relay_user_id, create=False)
        if not user:
            self.log.error(f"User {portal.mxid} not found")
            return web.json_response(
                data={"detail": {"message": f"Failed to get user {portal.mxid}"}},
                status=400,
                headers=self._acao_headers,
            )

        # Set the relay of the puppet
        try:
            await portal.set_relay_user(user)
        except Exception as e:
            self.log.error(f"Error setting the relay for portal {room_id}. Error: {e}")
            return web.json_response(
                data={
                    "detail": {
                        "message": f"Failed to set relay for user {portal.mxid} in portal {room_id}. Error:{e}"
                    }
                },
                status=400,
                headers=self._acao_headers,
            )

        self.log.debug(f"Set relay for user {portal.mxid} in portal {room_id}")
        return web.json_response(
            data={
                "detail": {
                    "message": f"Set relay for user {portal.mxid} in portal {room_id} was successful"
                }
            },
            status=200,
            headers=self._acao_headers,
        )

    async def validate_set_relay(self, request: web.Request) -> web.Response:
        """
        Validate if a specific room has a relay user set.

        Parameters
        ----------
        request: web.Request
            The request that contains the room_id in the path.
        Returns
        -------
        JSON
            The response of the request with a success message or an error message
        """
        self.log.debug("Validate set relay")

        user, _ = await self._get_user_and_body(request, read_body=False)

        try:
            room_id = request.match_info["room_id"]
        except KeyError:
            return web.json_response(
                data={"detail": {"message": "The room_id was not provided in the path"}},
                status=400,
                headers=self._acao_headers,
            )

        # Get the portal by room_id
        portal: Portal = await Portal.get_by_mxid(room_id)

        if not portal:
            self.log.error(f"Portal {room_id} not found")
            return web.json_response(
                data={
                    "detail": {
                        "message": f"Failed to get portal %(room_id)s",
                        "data": {"room_id": room_id},
                    },
                },
                status=400,
                headers=self._acao_headers,
            )

        if not portal.relay_user_id or portal.relay_user_id != user.mxid:
            self.log.debug(f"Portal {room_id} does not have a relay user set")
            return web.json_response(
                data={
                    "detail": {
                        "message": f"Portal %(room_id)s does not have a relay user set for user %(user_id)s",
                        "data": {"room_id": room_id, "user_id": user.mxid},
                    },
                },
                status=400,
                headers=self._acao_headers,
            )

        return web.json_response(
            data={
                "detail": {
                    "message": f"Portal %(room_id)s has relay user %(relay_user_id)s set",
                    "data": {"room_id": room_id, "relay_user_id": user.mxid},
                },
            },
            status=200,
            headers=self._acao_headers,
        )
