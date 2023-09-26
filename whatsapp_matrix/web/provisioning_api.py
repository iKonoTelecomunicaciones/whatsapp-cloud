from __future__ import annotations

import json
import logging
from asyncio import AbstractEventLoop, get_event_loop

from aiohttp import web

from ..db.whatsapp_application import WhatsappApplication
from ..user import User

logger = logging.getLogger()


class ProvisioningAPI:
    app: web.Application

    def __init__(
        self,
        shared_secret: str,
        loop: AbstractEventLoop = None,
    ) -> None:
        self.loop = loop or get_event_loop()
        self.app = web.Application(loop=self.loop)
        self.shared_secret = shared_secret

        self.app.router.add_route("POST", "/v1/register_app", self.register_app)
        self.app.router.add_route("PATCH", "/v1/update_app", self.update_app)

    @property
    def _access_headers(self) -> dict[str, str]:
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
            **self._access_headers,
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
                text=json.dumps({"detail": {"message": "All fields are mandatories"}}),
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
                            "message": f"This whatsapp_app {app_business_id} is already registered"
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the ws_phone_id is already registered
        if await WhatsappApplication.get_by_ws_phone_id(ws_phone_id=app_phone_id):
            return web.HTTPNotAcceptable(
                text=json.dumps(
                    {"detail": {"message": f"The phone_id {app_phone_id} is already registered"}}
                ),
                headers=self._headers,
            )

        # Create the whatsapp_app
        await WhatsappApplication.insert(
            name=app_name,
            admin_user=admin_user,
            business_id=app_business_id,
            ws_phone_id=app_phone_id,
            access_token=access_token,
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
        except json.JSONDecodeError:
            logger.error("Malformed JSON")
            raise web.HTTPUnprocessableEntity(
                text=json.dumps({"detail": {"message": "Malformed JSON"}}), headers=self._headers
            )

        return data

    def _missing_key_error(self, err: KeyError) -> None:
        """
        Return a HTTPBadRequest with the missing key

        Parameters
        ----------
        err : KeyError
            The missing key
        """
        logger.error(f"KeyError: {err}")
        raise web.HTTPNotAcceptable(
            text=json.dumps({"message": f"Missing key {err}"}), headers=self._headers
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
            logger.error(f"KeyError: {KeyError}")
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
                            "message": "The request has not data",
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
                            "message": f"The user {admin_user} is not registered",
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
                            "message": f"The Whatsapp application with user {admin_user}"
                            + "is not registered",
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

        logger.debug(f"Update whatsapp_app {whatsapp_app.business_id}")
        await whatsapp_app.update_by_admin_user(
            user=whatsapp_app.admin_user, values=data_to_update
        )

        return web.HTTPOk(
            text=json.dumps(
                {
                    "message": f"The whatsapp_app {whatsapp_app.business_id} has been updated",
                }
            ),
            headers=self._headers,
        )
