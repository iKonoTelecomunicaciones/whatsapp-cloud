from asyncio import AbstractEventLoop, get_event_loop
from logging import getLogger, Logger
from typing import Any, Dict, Optional, Tuple

from aiohttp import web

from meta_matrix.portal import Portal
from meta_matrix.user import User
from meta_matrix.db import MetaApplication as DBMetaApplication
from meta_matrix.config import Config
from .data import MetaMessageEvent, MetaMessageSender

from mautrix.types import SerializableAttrs


class MetaHandler:
    log: Logger = getLogger("meta.in")
    app: web.Application

    def __init__(self, loop: AbstractEventLoop = None, config: Config = None) -> None:
        self.loop = loop or get_event_loop()
        self.verify_token = config["bridge.provisioning.shared_secret"]
        self.app = web.Application(loop=self.loop)
        self.app.router.add_route("POST", "/receive", self.receive)
        self.app.router.add_route("GET", "/receive", self.verify_connection)

    async def _validate_event(
        self, data: Dict, type_class: SerializableAttrs
    ) -> Tuple[Any, Optional[web.Response]]:
        """It takes a dictionary of data, and a class, and returns a tuple of the class and an error
        Parameters
         ----------
         data : Dict
             The data that was sent to the server.
         type_class : Any
             The class that will be used to deserialize the data.
        Returns
         -------
             The return value is a tuple of the deserialized class and an error.
        """
        if (
            data.get("entry")[0].get("messaging")[0].get("message")
            and type_class == MetaMessageEvent
        ):
            class_initialiced: MetaMessageEvent = type_class.from_dict(data)
            if not class_initialiced.entry[0].messaging[0].message:
                return False
        else:
            return False

        return True

    async def verify_connection(self, request: web.Request) -> web.Response:
        if "hub.mode" in request.query:
            mode = request.query.get("hub.mode")
        if "hub.verify_token" in request.query:
            token = request.query.get("hub.verify_token")
        if "hub.challenge" in request.query:
            challenge = request.query.get("hub.challenge")

        if "hub.mode" in request.query_string and "hub.verify_token" in request.query:
            mode = request.query.get("hub.mode")
            token = request.query.get("hub.verify_token")

            if mode == "subscribe" and token == self.verify_token:
                self.log.info("The webhook has been verified.")

                challenge = request.query.get("hub.challenge")

                return web.Response(text=challenge, status=200)

            else:
                raise web.HTTPForbidden(text="The verify token is invalid.")

        else:
            raise web.HTTPConflict(
                text="The verify token is invalid. Please check the token and try again.",
            )

    async def receive(self, request: web.Request) -> None:
        """It receives a request from Meta, checks if the app is valid,
        and then calls the appropriate function to handle the event
        """
        data = dict(**await request.json())
        self.log.debug(f"The event arrives {data}")

        meta_page_id = data.get("entry")[0].get("id")

        if not meta_page_id in await DBMetaApplication.get_all_meta_apps():
            self.log.warning(
                f"Ignoring event because the meta_app [{meta_page_id}] is not registered."
            )
            return web.Response(status=406)

        if await self._validate_event(data, MetaMessageEvent):
            return await self.message_event(MetaMessageEvent.from_dict(data))
        # elif data.get("type") == GupshupEventType.MESSAGE_EVENT:
        #    return await self.status_event(data)
        # elif data.get("type") == GupshupEventType.USER_EVENT:
        #    # Ej: sandbox-start, opted-in, opted-out
        #    return web.Response(status=204)
        else:
            self.log.debug(f"Integration type not supported.")
            return web.Response(status=406)

    async def message_event(self, data: MetaMessageEvent) -> web.Response:
        """It validates the incoming request, fetches the portal associated with the sender,
        and then passes the message to the portal for handling
        """
        self.log.debug(f"Received Meta message event: {data}")
        sender = data.entry[0].messaging[0].sender
        page_id = data.entry[0].id
        user: User = await User.get_by_page_id(page_id)
        portal: Portal = await Portal.get_by_ps_id(sender.id, app_page_id=page_id)
        await portal.handle_meta_message(user, data, sender)
        return web.Response(status=204)

    # async def status_event(self, data: GupshupStatusEvent) -> web.Response:
    #    """It receives a Gupshup status event, validates it, and then passes it to the portal to handle"""
    #    self.log.debug(f"Received Gupshup status event: {data}")
    #    data, err = await self._validate_request(data, GupshupStatusEvent)
    #    if err is not None:
    #        self.log.error(f"Error handling incoming message: {err}")
    #    portal: po.Portal = await po.Portal.get_by_chat_id(
    #        self.generate_chat_id(gs_app=data.app, number=data.payload.destination)
    #    )
    #    await portal.handle_gupshup_status(data.payload)
    #    return web.Response(status=204)
