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

    @property
    def _acao_headers(self) -> dict[str, str]:
        """
        Return the Access-Control-Allows headers

        """
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
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
        if not meta_app_name:
            return web.HTTPBadRequest(
                text=json.dumps({"error": "meta_app_name not entered", "state": "missing-field"}),
                headers=self._headers,
            )
        elif not meta_app_page_id:
            return web.HTTPBadRequest(
                text=json.dumps(
                    {"error": "meta_app_page_id not entered", "state": "missing-field"}
                ),
                headers=self._headers,
            )
        elif not meta_outgoing_page_id:
            return web.HTTPBadRequest(
                text=json.dumps(
                    {"error": "meta_outgoing_page_id not entered", "state": "missing-field"}
                ),
                headers=self._headers,
            )
        elif not meta_page_access_token:
            return web.HTTPBadRequest(
                text=json.dumps(
                    {"error": "meta_page_access_token not entered", "state": "missing-field"}
                ),
                headers=self._headers,
            )
        elif not notice_room:
            return web.HTTPBadRequest(
                text=json.dumps({"error": "notice_room not entered", "state": "missing-field"}),
                headers=self._headers,
            )
        elif not admin_user:
            return web.HTTPBadRequest(
                text=json.dumps({"error": "admin_user not entered", "state": "missing-field"}),
                headers=self._headers,
            )

        try:
            # Check if the user is already registered
            if await User.get_by_mxid(mxid=admin_user, create=False):
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

            # Create the user and add the page_id and the notice_room
            user: User = await User.get_by_mxid(mxid=admin_user)
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


# async def login_options(self, _: web.Request) -> web.Response:
#    return web.Response(status=200, headers=self._headers)
#
# async def _resolve_identifier(self, number: str) -> pu.Puppet:
#    try:
#        number = normalize_number(number).replace("+", "")
#    except Exception as e:
#        raise web.HTTPBadRequest(text=json.dumps({"error": str(e)}), headers=self._headers)
#
#    puppet: pu.Puppet = await pu.Puppet.get_by_phone(number)
#
#    return puppet
#
# async def start_pm(self, request: web.Request) -> web.Response:
#    user = await self.check_token(request)
#    puppet = await self._resolve_identifier(request.match_info["number"])
#
#    portal = await po.Portal.get_by_chat_id(
#        chat_id=f"{user.gs_app}-{puppet.phone}", create=True
#    )
#
#    if portal.mxid:
#        await portal.main_intent.invite_user(portal.mxid, user.mxid)
#        just_created = False
#    else:
#        chat_info = {
#            "app": f"{user.gs_app}-{puppet.phone}",
#        }
#        info = ChatInfo.deserialize(chat_info)
#        chat_customer = {"phone": puppet.phone, "name": puppet.name or puppet.custom_mxid}
#        customer = GupshupMessageSender.deserialize(chat_customer)
#        info.sender = customer
#        await portal.create_matrix_room(user, info)
#        just_created = True
#    return web.json_response(
#        {
#            "room_id": portal.mxid,
#            "just_created": just_created,
#            "chat_id": portal.chat_id,
#            "other_user": {
#                "mxid": puppet.mxid,
#                "displayname": puppet.name,
#            },
#        },
#        headers=self._acao_headers,
#        status=201 if just_created else 200,
#    )
#
# async def template(self, request: web.Request) -> web.Response:
#    user, data = await self._get_user(request)
#
#    try:
#        room_id = data["room_id"]
#        template_message = data["template_message"]
#
#    except KeyError as e:
#        raise self._missing_key_error(e)
#    if not room_id:
#        return web.json_response(
#            data={"error": "room_id not entered", "state": "missing-field"},
#            status=400,
#            headers=self._acao_headers,
#        )
#    elif not template_message:
#        return web.json_response(
#            data={"error": "template_message not entered", "state": "missing-field"},
#            status=400,
#            headers=self._acao_headers,
#        )
#
#    msg = TextMessageEventContent(body=template_message, msgtype=MessageType.TEXT)
#    msg.trim_reply_fallback()
#
#    portal: po.Portal = await po.Portal.get_by_mxid(room_id)
#    if not portal:
#        return web.json_response(
#            data={"error": f"Failed to get room {room_id}"},
#            status=400,
#            headers=self._acao_headers,
#        )
#
#    msg_event_id = await portal.az.intent.send_message(portal.mxid, msg)
#
#    await portal.handle_matrix_message(
#        sender=user,
#        message=msg,
#        event_id=msg_event_id,
#        is_gupshup_template=True,
#    )
#
#    return web.json_response(
#        data={"detail": "Template has been sent", "event_id": msg_event_id}
#    )
#
# async def interactive_message(self, request: web.Request) -> web.Response:
#    """
#    QuickReplay:
#
#    ```
#    {
#        "room_id": "!foo:foo.com",
#        "interactive_message": {
#            "type": "quick_reply",
#            "content": {
#                "type": "text",
#                "header": "Hello, This is the header.\n\n",
#                "text": "Please select one of the following options",
#                "caption": "",
#                "filename": null,
#                "url": null
#            },
#            "options": [
#                {"type": "text", "title": "I agree", "description": null, "postbackText": null},
#                {"type": "text", "title": "No Accept", "description": null, "postbackText": null}
#            ]
#        }
#    }
#    ```
#
#
#    ListReplay:
#
#    ```
#    {
#        "room_id": "!foo:foo.com",
#        "interactive_message": {
#            "type": "list",
#            "title": "Main title",
#            "body": "Hello World",
#            "msgid": "!foo:foo.com",
#            "globalButtons": [{"type": "text", "title": "Open"}],
#            "items": [
#                {
#                    "title": "Section title",
#                    "subtitle": "SubSection title",
#                    "options": [
#                        {
#                            "type": "text",
#                            "title": "Option 1",
#                            "description": null,
#                            "postbackText": "1"
#                        },
#                        {
#                            "type": "text",
#                            "title": "Option 2",
#                            "description": null,
#                            "postbackText": "2"
#                        },
#                        {
#                            "type": "text",
#                            "title": "Option 3",
#                            "description": null,
#                            "postbackText": "3"
#                        },
#                        {
#                            "type": "text",
#                            "title": "Option 4",
#                            "description": null,
#                            "postbackText": "4"
#                        }
#                    ]
#                }
#            ]
#        }
#    }
#    ```
#    """
#    user, data = await self._get_user(request)
#
#    try:
#        room_id = data["room_id"]
#        interactive_message = data["interactive_message"]
#    except KeyError as e:
#        raise self._missing_key_error(e)
#
#    if not room_id:
#        return web.json_response(
#            data={"error": "room_id not entered", "state": "missing-field"},
#            status=400,
#            headers=self._acao_headers,
#        )
#    elif not interactive_message:
#        return web.json_response(
#            data={"error": "interactive_message not entered", "state": "missing-field"},
#            status=400,
#            headers=self._acao_headers,
#        )
#
#    interactive_message = InteractiveMessage.deserialize(interactive_message)
#
#    msg = TextMessageEventContent(
#        body=interactive_message.message,
#        msgtype=MessageType.TEXT,
#        formatted_body=markdown(interactive_message.message.replace("\n", "<br>")),
#        format=Format.HTML,
#    )
#
#    msg.trim_reply_fallback()
#
#    portal = await po.Portal.get_by_mxid(room_id)
#
#    if not portal:
#        return web.json_response(
#            data={"error": f"Failed to get room {room_id}"},
#            status=400,
#            headers=self._acao_headers,
#        )
#    msg_event_id = await portal.az.intent.send_message(
#        portal.mxid, msg
#    )  # only be visible to the agent
#    await portal.handle_matrix_message(
#        sender=user,
#        message=msg,
#        event_id=msg_event_id,
#        additional_data=interactive_message.serialize(),
#    )
#
#    return web.json_response(data={"detail_1": interactive_message.message})
#
# async def _get_user(self, request: web.Request, read_body: bool = True) -> tuple[u.User, JSON]:
#    user = await self.check_token(request)
#
#    if read_body:
#        try:
#            data = await request.json()
#        except json.JSONDecodeError:
#            raise web.HTTPBadRequest(text='{"error": "Malformed JSON"}', headers=self._headers)
#    else:
#        data = None
#    return user, data
#
