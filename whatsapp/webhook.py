import json
from asyncio import AbstractEventLoop, get_event_loop
from logging import Logger, getLogger

from aiohttp import web

from whatsapp_matrix.config import Config
from whatsapp_matrix.db import WhatsappApplication as DBWhatsappApplication
from whatsapp_matrix.portal import Portal
from whatsapp_matrix.room_sync_messages import RoomSyncMessages
from whatsapp_matrix.user import User

from .data import WhatsappEvent


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

        elif "message_echoes" in wb_value:
            return await self.send_echo_event(data)

        # If the event is a read, we send a read event to matrix
        elif wb_value.get("statuses") and wb_value.get("statuses")[0].get("status") == "read":
            return await self.read_event(WhatsappEvent.from_dict(data))

        # If the event is an error, we send to the user the message error
        elif wb_value.get("statuses") and wb_value.get("statuses")[0].get("status") == "failed":
            wb_event = WhatsappEvent.from_dict(data)
            wb_statuses = wb_event.entry.changes.value.statuses
            # Get the customer phone
            customer_phone = wb_event.entry.changes.value.contacts.wa_id
            customer_bsuid = wb_event.entry.changes.value.contacts.user_id
            # Get the error information
            message_error = wb_statuses.errors.error_data.details

            if customer_phone is None and customer_bsuid is None:
                self.log.error(
                    f"Failed to handle the error event because the recipient identifier is missing. "
                    f"Business ID: {wb_business_id}, Event: {data}"
                )
                return web.Response(status=200)

            portal: Portal = await Portal.get_by_app_and_identifier(
                phone_id=customer_phone,
                bsuid=customer_bsuid,
                app_business_id=wb_business_id,
                create=False,
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

        if sender.wa_id is None and sender.user_id is None:
            self.log.error(
                f"Failed to handle the error event because the recipient identifier is missing. "
                f"Business ID: {business_id}, Event: {data}"
            )
            return web.Response(status=200)

        portal: Portal = await Portal.get_by_app_and_identifier(
            phone_id=sender.wa_id, bsuid=sender.user_id, app_business_id=business_id
        )

        with RoomSyncMessages(portal.mxid) as message_lock:
            async with message_lock:
                if data.entry.changes.value.messages.errors:
                    await portal.handle_whatsapp_errors(
                        user, data.entry.changes.value.messages, sender
                    )
                elif data.entry.changes.value.messages.type == "reaction":
                    await portal.handle_whatsapp_reaction(data, sender)
                elif data.entry.changes.value.messages.type == "edit":
                    await portal.handle_whatsapp_edit(
                        sender_id=sender.wa_id or sender.user_id,
                        message_to_edit=data.entry.changes.value.messages,
                        intent=portal.main_intent,
                    )
                elif data.entry.changes.value.messages.type == "system":
                    self.log.info(
                        f"Received a system message of type "
                        f"{data.entry.changes.value.messages.system.type} from user {sender.wa_id} "
                        f"for business account {business_id}. "
                        f"Message: {data.entry.changes.value.messages.system.body}"
                    )
                else:
                    await portal.handle_whatsapp_message(user, data, sender)

        return web.Response(status=200)

    async def read_event(self, data: WhatsappEvent) -> web.Response:
        """
        It validates the incoming request, fetches the portal associated with the sender,
        and then passes the event to the portal for handling
        """
        self.log.debug(f"Received Whatsapp Cloud read event: {data}")
        # Get the phone id and the business id
        phone_id = data.entry.changes.value.contacts.wa_id
        bsuid = data.entry.changes.value.contacts.user_id

        business_id = data.entry.id
        # Get the portal
        portal: Portal = await Portal.get_by_app_and_identifier(
            phone_id=phone_id, bsuid=bsuid, app_business_id=business_id, create=False
        )
        # Handle the read event
        if portal:
            message_id = data.entry.changes.value.statuses.id
            await portal.handle_whatsapp_read(message_id=message_id)
            return web.Response(status=200)
        else:
            self.log.error(f"Portal not found.")
            return web.Response(status=406)

    async def send_echo_event(self, data: dict) -> web.Response:
        """
        Validates the incoming request, fetches the portal associated with the sender,
        and then sends the echo event to the portal for handling

        Params
        ------
        data: The incoming echo event data, usually contains the message sent by the customer
        in WhatsApp and the sender information

        Returns
        -------
        web.Response: The response to be sent back to the WhatsApp Cloud
        """
        self.log.debug(f"Received Whatsapp Cloud echo event: {data}")

        # Parse the data using WhatsappEvent structure
        wb_event = WhatsappEvent.from_dict(data)
        wb_value = wb_event.entry.changes.value
        business_id = wb_event.entry.id

        # Get the user associated with this business account
        user: User = await User.get_by_business_id(business_id)
        if not user:
            self.log.error(f"No user found for business_id {business_id}")
            return web.Response(status=200)

        # Process each echo message
        if not wb_value.message_echoes:
            self.log.warning(f"No message echoes found in the event for business_id {business_id}")
            return web.Response(status=200)

        for echo_message in wb_value.message_echoes:
            # The 'to' field contains the recipient's phone (the customer)
            customer_phone = echo_message.to
            customer_bsuid = wb_value.contacts.user_id

            # Get the portal for this conversation
            portal: Portal = await Portal.get_by_app_and_identifier(
                phone_id=customer_phone, bsuid=customer_bsuid, app_business_id=business_id
            )

            with RoomSyncMessages(portal.mxid) as message_lock:
                async with message_lock:
                    # Handle the echo message using the portal
                    if echo_message.type == "edit":
                        await portal.handle_whatsapp_edit(
                            sender_id=user.mxid,
                            message_to_edit=echo_message,
                            intent=portal.az.intent,
                        )
                    else:
                        await portal.handle_whatsapp_echo(user=user, echo_message=echo_message)

        return web.Response(status=200)
