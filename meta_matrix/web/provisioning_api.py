from __future__ import annotations

import json
import logging
from asyncio import AbstractEventLoop, get_event_loop

from aiohttp import web

from ..db.meta_application import MetaApplication
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
        Register a new Meta app with his matrix user

        Parameters
        ----------
        request : web.Request
            The request that contains the data of the app and the user.

        """
        # Obtain the data from the request
        data = await self._get_body(request)

        try:
            # Separate the data from the request
            meta_app_name = data["meta_app_name"]
            meta_app_page_id = data["meta_app_page_id"]
            meta_outgoing_page_id = data["meta_outgoing_page_id"]
            meta_page_access_token = data["meta_page_access_token"]
            notice_room = data["notice_room"]
            admin_user = data["admin_user"]
        except KeyError as e:
            raise self._missing_key_error(e)

        # Check if the data does not empty
        if (
            not meta_app_name
            or not meta_app_page_id
            or not meta_outgoing_page_id
            or not meta_page_access_token
            or not notice_room
            or not admin_user
        ):
            return web.HTTPBadRequest(
                text=json.dumps({"error": "All fields are mandatories", "state": "missing-field"}),
                headers=self._headers,
            )

        try:
            # Check if the user is already registered, this acd user can register because the
            # bridge register the acd user when listeng that the acd user is created in the control room
            user: User = await User.get_by_mxid(mxid=admin_user)
            if user.app_page_id:
                return web.HTTPUnprocessableEntity(
                    text=json.dumps({"error": "You already have a registered meta_app"}),
                    headers=self._headers,
                )

            # Check if the meta_app is already registered
            if await MetaApplication.get_by_page_id(page_id=meta_app_page_id):
                return web.HTTPUnprocessableEntity(
                    text=json.dumps(
                        {"error": f"This meta_app {meta_app_page_id} is already registered"}
                    ),
                    headers=self._headers,
                )

            # Create the meta_app
            await MetaApplication.insert(
                name=meta_app_name,
                admin_user=admin_user,
                page_id=meta_app_page_id,
                outgoing_page_id=meta_outgoing_page_id,
                page_access_token=meta_page_access_token,
            )

            # Add the page_id and the notice_room
            user.app_page_id = meta_app_page_id
            user.notice_room = notice_room
            await user.update()

        except Exception as e:
            logger.error(f"Error: {e}")
            return web.HTTPUnprocessableEntity(
                text=json.dumps({"error": e}),
                headers=self._headers,
            )

        return web.HTTPOk(
            text=json.dumps({"detail": "Meta application has been created"}), headers=self._headers
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
            raise web.HTTPBadRequest(
                text=json.dumps({"error": "Malformed JSON"}), headers=self._headers
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
        raise web.HTTPBadRequest(
            text=json.dumps({"error": f"Missing key {err}"}), headers=self._headers
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
            raise web.HTTPBadRequest(
                text=json.dumps({"error": "Missing Authorization header"}), headers=self._headers
            )
        # Validate the token
        if token != self.shared_secret:
            raise web.HTTPForbidden(
                text=json.dumps({"error": "Invalid token"}), headers=self._headers
            )

    async def update_app(self, request: web.Request) -> dict:
        """
        Update the meta_app

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
                            "data": None,
                            "message": f"The request does not have data",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Separate the data from the request
        app_name = data.get("app_name", None)
        page_token = data.get("page_access_token", None)
        admin_user = request.query.get("user_id", None)

        if not admin_user:
            return web.HTTPUnprocessableEntity(
                text=json.dumps(
                    {
                        "detail": {
                            "data": None,
                            "message": f"The user was not provided",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the user is registered
        user: User = await User.get_by_mxid(mxid=admin_user, create=False)
        if not user:
            return web.HTTPUnprocessableEntity(
                text=json.dumps(
                    {
                        "detail": {
                            "data": None,
                            "message": f"The user {admin_user} is not registered",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Check if the meta_app is registered
        meta_app: MetaApplication = await MetaApplication.get_by_admin_user(admin_user=admin_user)

        if not meta_app:
            return web.HTTPUnprocessableEntity(
                text=json.dumps(
                    {
                        "detail": {
                            "data": None,
                            "message": f"""The meta application with user {admin_user}
                                        is not registered""",
                        }
                    }
                ),
                headers=self._headers,
            )

        # Update the meta_app with the send values
        data_to_update = (
            app_name if app_name else meta_app.name,
            page_token if page_token else meta_app.page_access_token,
        )

        logger.debug(f"Update meta_app {meta_app.page_id}")
        await meta_app.update_by_admin_user(user=meta_app.admin_user, values=data_to_update)

        return web.HTTPOk(
            text=json.dumps(
                {
                    "detail": {
                        "data": None,
                        "message": f"The meta_app {meta_app.page_id} has been updated",
                    }
                }
            ),
            headers=self._headers,
        )
