from asyncio import AbstractEventLoop, get_event_loop
from logging import Logger, getLogger

from aiohttp import web

from whatsapp_matrix.config import Config
from whatsapp_matrix.db import WhatsappApplication as DBWhatsappApplication
from whatsapp_matrix.portal import Portal
from whatsapp_matrix.user import User

from .data import WhatsappMessageEvent


class WhatsappHandler:
    log: Logger = getLogger("whatsapp.in")
    app: web.Application

    def __init__(self, loop: AbstractEventLoop = None, config: Config = None) -> None:
        self.loop = loop or get_event_loop()
        self.verify_token = config["bridge.provisioning.shared_secret"]
        self.app = web.Application(loop=self.loop)
        self.app.router.add_route("POST", "/receive", self.receive)
        self.app.router.add_route("GET", "/receive", self.verify_connection)

    async def verify_connection(self, request: web.Request) -> web.Response:
        """
        Verify the connection between the bridge and Whatsapp Api.
        """
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
        """It receives a request from Whatsapp, checks if the app is valid,
        and then calls the appropriate function to handle the event
        """
        data = dict(**await request.json())
        self.log.debug(f"The event arrives {data}")

        ws_business_id = data.get("entry")[0].get("id")
        ws_value = data.get("entry")[0].get("changes")[0].get("value")
        ws_apps = await DBWhatsappApplication.get_all_ws_apps()

        # Validate if the app is registered
        if not ws_business_id in ws_apps:
            self.log.warning(
                f"Ignoring event because the whatsapp_app [{ws_business_id}] is not registered."
            )
            return web.Response(status=406)

        # Validate if the event is a message
        if ws_value.get("messages"):
            return await self.message_event(WhatsappMessageEvent.from_dict(data))
        else:
            self.log.debug(f"Integration type not supported.")
            return web.Response(status=406)

    async def message_event(self, data: WhatsappMessageEvent) -> web.Response:
        """It validates the incoming request, fetches the portal associated with the sender,
        and then passes the message to the portal for handling
        """
        self.log.debug(f"Received Whatsapp Cloud message event: {data}")
        sender = data.entry.changes.value.contacts
        business_id = data.entry.id
        user: User = await User.get_by_business_id(business_id)
        portal: Portal = await Portal.get_by_phone_id(sender.wa_id, app_business_id=business_id)

        await portal.handle_whatsapp_message(user, data, sender)
        return web.Response(status=200)
