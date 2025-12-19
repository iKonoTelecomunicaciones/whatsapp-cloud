import json
from asyncio import AbstractEventLoop, get_event_loop
from logging import Logger, getLogger

from aiohttp import web

from whatsapp_matrix.config import Config
from whatsapp_matrix.db import WhatsappApplication as DBWhatsappApplication
from whatsapp_matrix.portal import Portal
from whatsapp_matrix.user import User

from .data import WhatsappEvent, WhatsappStatusesEvent


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
                raise web.HTTPForbidden(
                    json.dumps(
                        {
                            "detail": {
                                "message": "The verify token is invalid.",
                            }
                        }
                    )
                )

        else:
            raise web.HTTPConflict(
                text=json.dumps(
                    {
                        "detail": {
                            "message": (
                                "The verify token is invalid. Please check the token "
                                "and try again."
                            )
                        }
                    }
                ),
            )

    async def receive(self, request: web.Request) -> None:
        """It receives a request from Whatsapp, checks if the app is valid,
        and then calls the appropriate function to handle the event
        """
        data = dict(**await request.json())
        self.log.debug(f"The event arrives {data}")

        # Get the business id and the value of the event
        wb_business_id = data.get("entry")[0].get("id")
        wb_value = data.get("entry")[0].get("changes")[0].get("value")
        # Get all the whatsapp apps
        wb_apps = await DBWhatsappApplication.get_all_wb_apps()

        # Validate if the app is registered
        if not wb_business_id in wb_apps:
            self.log.warning(
                f"Ignoring event because the whatsapp_app [{wb_business_id}] is not registered."
            )
            return web.Response(status=200)

        # Validate if the event is a message, read or error
        # If the event is a message, we send a message event to matrix
        if wb_value.get("messages"):
            return await self.message_event(WhatsappEvent.from_dict(data))

        # If the event is a read, we send a read event to matrix
        elif wb_value.get("statuses") and wb_value.get("statuses")[0].get("status") == "read":
            return await self.read_event(WhatsappEvent.from_dict(data))

        # If the event is an error, we send to the user the message error
        elif wb_value.get("statuses") and wb_value.get("statuses")[0].get("status") == "failed":
            wb_statuses = WhatsappStatusesEvent.from_dict(wb_value.get("statuses")[0])
            # Get the customer phone
            customer_phone = wb_statuses.recipient_id
            # Get the error information
            message_error = wb_statuses.errors.error_data.details

            portal: Portal = await Portal.get_by_app_and_phone_id(
                phone_id=customer_phone, app_business_id=wb_business_id, create=False
            )
            if portal:
                await portal.handle_whatsapp_error(message_error=message_error)
            return web.Response(status=200)

        else:
            self.log.debug(f"Integration type not supported.")
            return web.Response(status=200)

    async def message_event(self, data: WhatsappEvent) -> web.Response:
        """It validates the incoming request, fetches the portal associated with the sender,
        and then passes the message to the portal for handling
        """
        self.log.debug(f"Received Whatsapp Cloud message event: {data}")
        sender = data.entry.changes.value.contacts
        business_id = data.entry.id
        user: User = await User.get_by_business_id(business_id)
        portal: Portal = await Portal.get_by_app_and_phone_id(
            phone_id=sender.wa_id, app_business_id=business_id
        )

        await portal.publish_whatsapp_event(event=data, user=user, sender=sender)

        return web.Response(status=200)

    async def read_event(self, data: WhatsappEvent) -> web.Response:
        """
        It validates the incoming request, fetches the portal associated with the sender,
        and then passes the event to the portal for handling
        """
        self.log.debug(f"Received Whatsapp Cloud read event: {data}")
        # Get the phone id and the business id
        wa_id = data.entry.changes.value.statuses.recipient_id
        business_id = data.entry.id
        # Get the portal
        portal: Portal = await Portal.get_by_app_and_phone_id(
            phone_id=wa_id, app_business_id=business_id, create=False
        )
        # Handle the read event
        if portal:
            message_id = data.entry.changes.value.statuses.id
            await portal.handle_whatsapp_read(message_id=message_id)
            return web.Response(status=200)
        else:
            self.log.error(f"Portal not found.")
            return web.Response(status=406)
