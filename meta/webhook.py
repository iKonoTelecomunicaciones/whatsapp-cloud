from asyncio import AbstractEventLoop, get_event_loop
from logging import Logger, getLogger

from aiohttp import web

from meta_matrix.config import Config
from meta_matrix.db import MetaApplication as DBMetaApplication
from meta_matrix.portal import Portal
from meta_matrix.user import User

from .data import MetaMessageEvent, MetaStatusEvent


class MetaHandler:
    log: Logger = getLogger("meta.in")
    app: web.Application

    def __init__(self, loop: AbstractEventLoop = None, config: Config = None) -> None:
        self.loop = loop or get_event_loop()
        self.verify_token = config["bridge.provisioning.shared_secret"]
        self.app = web.Application(loop=self.loop)
        self.app.router.add_route("POST", "/receive", self.receive)
        self.app.router.add_route("GET", "/receive", self.verify_connection)

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
        meta_messaging = data.get("entry")[0].get("messaging")[0]
        meta_apps = await DBMetaApplication.get_all_meta_apps()
        if not meta_page_id in meta_apps:
            self.log.warning(
                f"Ignoring event because the meta_app [{meta_page_id}] is not registered."
            )
            return web.Response(status=406)

        if "message" in meta_messaging and not meta_messaging.get("message").get("is_echo"):
            return await self.message_event(MetaMessageEvent.from_dict(data))
        elif "delivery" in meta_messaging or "read" in meta_messaging:
            return await self.status_event(MetaStatusEvent.from_dict(data))
        else:
            self.log.debug(f"Integration type not supported.")
            return web.Response(status=406)

    async def message_event(self, data: MetaMessageEvent) -> web.Response:
        """It validates the incoming request, fetches the portal associated with the sender,
        and then passes the message to the portal for handling
        """
        self.log.debug(f"Received Meta message event: {data}")
        sender = data.entry.messaging.sender
        page_id = data.entry.id
        if data.object == "page":
            meta_origin = "fb"
        elif data.object == "instagram":
            meta_origin = "ig"
        user: User = await User.get_by_page_id(page_id)
        portal: Portal = await Portal.get_by_ps_id(
            sender.id, app_page_id=page_id, meta_origin=meta_origin
        )

        await portal.handle_meta_message(user, data, sender)
        return web.Response(status=204)

    async def status_event(self, status_event: MetaStatusEvent) -> web.Response:
        """It receives a Meta status event, validates it,
        and then passes it to the portal to handle
        """
        self.log.debug(f"Received Meta status event: {status_event}")
        sender = status_event.entry.messaging.sender
        portal: Portal = await Portal.get_by_ps_id(
            ps_id=sender.id, app_page_id=status_event.entry.id, create=False
        )
        await portal.handle_meta_status(status_event)
        return web.Response(status=204)
