from __future__ import annotations

from asyncio import Lock
from datetime import datetime
from string import Template
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from aiohttp import ClientConnectorError
from markdown import markdown
from mautrix.appservice import AppService, IntentAPI
from mautrix.bridge import BasePortal
from mautrix.types import (
    EventID,
    EventType,
    FileInfo,
    Format,
    LocationMessageEventContent,
    MediaMessageEventContent,
    MessageEventContent,
    MessageType,
    PowerLevelStateEventContent,
    ReactionEventContent,
    RoomID,
    TextMessageEventContent,
    UserID,
)

from whatsapp.api import WhatsappClient
from whatsapp.data import WhatsappContacts, WhatsappEvent, WhatsappReaction
from whatsapp.interactive_message import EventInteractiveMessage
from whatsapp.types import WhatsappMessageID, WhatsappPhone, WsBusinessID
from whatsapp_matrix.formatter.from_matrix import matrix_to_whatsapp
from whatsapp_matrix.formatter.from_whatsapp import whatsapp_reply_to_matrix

from .db import Message as DBMessage
from .db import Portal as DBPortal
from .db import Reaction as DBReaction
from .db import WhatsappApplication as DBWhatsappApplication
from .formatter import whatsapp_to_matrix
from .puppet import Puppet
from .user import User

if TYPE_CHECKING:
    from .__main__ import WhatsappBridge

StateBridge = EventType.find("m.bridge", EventType.Class.STATE)
StateHalfShotBridge = EventType.find("uk.half-shot.bridge", EventType.Class.STATE)

InviteList = Union[UserID, List[UserID]]


class Portal(DBPortal, BasePortal):
    by_mxid: Dict[RoomID, "Portal"] = {}
    by_phone_id: Dict[WhatsappPhone, "Portal"] = {}

    message_template: Template
    federate_rooms: bool
    invite_users: List[UserID]
    initial_state: Dict[str, Dict[str, Any]]
    auto_change_room_name: bool

    az: AppService
    private_chat_portal_whatsapp: bool
    whatsapp_client: WhatsappClient

    _main_intent: Optional[IntentAPI] | None
    _create_room_lock: Lock
    _send_lock: Lock

    def __init__(
        self,
        phone_id: str,
        app_business_id: str,
        mxid: Optional[RoomID] = None,
        relay_user_id: UserID | None = None,
    ) -> None:
        super().__init__(phone_id, app_business_id, mxid, relay_user_id)
        BasePortal.__init__(self)
        self._create_room_lock = Lock()
        self._send_lock = Lock()
        self.log = self.log.getChild(self.phone_id or self.mxid)
        self._main_intent: IntentAPI = None
        self._relay_user = None
        self.error_codes = self.config["whatsapp.error_codes"]
        self.homeserver_address = self.config["homeserver.public_address"]
        self.google_maps_url = self.config["bridge.whatsapp_cloud.google_maps_url"]
        self.openstreetmap_url = self.config["bridge.whatsapp_cloud.openstreetmap_url"]

    @property
    def main_intent(self) -> IntentAPI:
        if not self._main_intent:
            raise ValueError("Portal must be postinited before main_intent can be used")
        return self._main_intent

    @property
    async def init_whatsapp_client(self) -> Dict:
        try:
            whatsapp_app = await DBWhatsappApplication.get_by_business_id(
                business_id=self.app_business_id
            )
        except Exception as e:
            self.log.exception(e)
            return

        self.whatsapp_client.page_access_token = whatsapp_app.page_access_token
        self.whatsapp_client.business_id = whatsapp_app.business_id
        self.whatsapp_client.wb_phone_id = whatsapp_app.wb_phone_id

    @property
    def is_direct(self) -> bool:
        return self.phone_id is not None

    @classmethod
    def init_cls(cls, bridge: "WhatsappBridge") -> None:
        cls.config = bridge.config
        cls.matrix = bridge.matrix
        cls.az = bridge.az
        cls.loop = bridge.loop
        BasePortal.bridge = bridge
        cls.private_chat_portal_whatsapp = cls.config["bridge.private_chat_portal_whatsapp"]
        cls.whatsapp_client = bridge.whatsapp_client

    def send_text_message(self, message: str) -> Optional[EventID]:
        """
        Takes a message from Whatsapp, checks the kind of message and change the format of it to a
        valid format of Matrix message and sends it to Matrix

        Parameters
        ----------
        source : User
            The class that will be used to specify who receives the message.

        message : MessageEventContent
            The class that containt the data of the message.
        """
        html, text = whatsapp_to_matrix(message)
        content = TextMessageEventContent(msgtype=MessageType.TEXT, body=message)
        # Validate if the message has a html format
        if html is not None:
            content.format = Format.HTML
            content.formatted_body = html
        # Send the message to Matrix
        return self.main_intent.send_message(self.mxid, content)

    async def create_matrix_room(self, source: User, sender: WhatsappContacts) -> RoomID:
        """
        Create a matrix room where to contact with the customer

        Parameters
        ----------
        source : User
            The class that will be used to specify who receives the message.

        sender : Dict
            Dictionary that contains the data of who sends the message.

        Exceptions
        ----------
        Exception:
            Show and error if the portal does not create.
        """
        # Validate if the matrix room exists, if not, it is created
        if self.mxid:
            return self.mxid
        async with self._create_room_lock:
            try:
                self.phone_id = sender.wa_id
                return await self._create_matrix_room(source=source, sender=sender)
            except Exception as error:
                self.log.exception(f"Failed to create portal: {error}")
                return None

    async def _create_matrix_room(self, source: User, sender: WhatsappContacts) -> RoomID:
        """
        Create and configure a matrix room

        Parameters
        ----------
        source : User
            The class that will be used to specify who receives the message.

        sender : Dict
            Dictionary that contains the data of who sends the message.
        """
        self.log.debug("Creating Matrix room")

        # Add the initial permissions to the room
        power_levels = await self._get_power_levels(is_initial=True)
        initial_state = [
            {
                "type": str(StateBridge),
                "state_key": self.bridge_info_state_key,
                "content": self.bridge_info,
            },
            # TODO remove this once https://github.com/matrix-org/matrix-doc/pull/2346 is in spec
            {
                "type": str(StateHalfShotBridge),
                "state_key": self.bridge_info_state_key,
                "content": self.bridge_info,
            },
            {
                "type": str(EventType.ROOM_POWER_LEVELS),
                "content": power_levels.serialize(),
            },
        ]

        invites = [source.mxid]
        creation_content = {}
        room_name_variables = {
            "userid": sender.wa_id,
            "displayname": f"{sender.profile.name}",
        }
        room_name_template: str = self.config["bridge.whatsapp_cloud.room_name_template"]

        if not self.config["bridge.federate_rooms"]:
            creation_content["m.federate"] = False

        # Create the room with the name user, and add the initial permissions to the room
        self.mxid = await self.main_intent.create_room(
            name=room_name_template.format(**room_name_variables),
            is_direct=self.is_direct,
            initial_state=initial_state,
            invitees=invites,
            topic="Whatsapp private chat",
            creation_content=creation_content,
        )
        self.relay_user_id = source.mxid

        # Validate if the room was created
        if not self.mxid:
            raise Exception("Failed to create room: no mxid returned")

        # Add the mxid to the database
        await self.update()
        self.log.debug(f"Matrix room created: {self.mxid}")
        self.by_mxid[self.mxid] = self

        # Obtain the puppet of the user and update the information
        puppet: Puppet = await Puppet.get_by_phone_id(
            self.phone_id, app_business_id=self.app_business_id
        )

        await puppet.update_info(sender)

        # Invite the user to the room
        await self.main_intent.invite_user(
            self.mxid, source.mxid, extra_content=self._get_invite_content(puppet)
        )

        return self.mxid

    async def handle_matrix_leave(self, user: User) -> None:
        if self.is_direct:
            self.log.info(f"{user.mxid} left private chat portal with {self.mxid}")
            if await Puppet.get_by_mxid(user.mxid, create=False):
                self.log.info(
                    f"{user.mxid} was the recipient of this portal. Cleaning up and deleting..."
                )
                await self.cleanup_and_delete()
        else:
            self.log.debug(f"{user.mxid} left portal {self.mxid}")

    def _get_invite_content(self, double_puppet: Puppet | None) -> dict[str, Any]:
        invite_content = {}
        if double_puppet:
            invite_content["fi.mau.will_auto_accept"] = True
        if self.is_direct:
            invite_content["is_direct"] = True
        return invite_content

    async def _get_power_levels(
        self, levels: PowerLevelStateEventContent | None = None, is_initial: bool = False
    ) -> PowerLevelStateEventContent:
        """
        Created the power levels of the room

        Parameters
        ----------
        levels : PowerLevelStateEventContent
            The class that containt the data of the power levels.

        is_initial : bool
            Variable that indicates if the power levels are the initial ones.
        """
        levels = levels or PowerLevelStateEventContent()
        default_power_levels = self.config["bridge.default_power_levels"]
        default_events_levels = self.config["bridge.default_events_levels"]
        default_user_levels = self.config["bridge.default_user_levels"]

        for key, value in default_power_levels.items():
            setattr(levels, key, value)

        for key, value in default_events_levels.items():
            levels.events[getattr(EventType, key)] = value

        if self.main_intent.mxid not in levels.users:
            levels.users[self.main_intent.mxid] = default_user_levels if is_initial else 100

        return levels

    @property
    def bridge_info_state_key(self) -> str:
        return f"com.github.whatsapp-cloud://whatsapp-cloud/{self.phone_id}"

    @property
    def bridge_info(self) -> Dict[str, Any]:
        return {
            "bridgebot": self.az.bot_mxid,
            "creator": self.main_intent.mxid,
            "protocol": {
                "id": "whatsapp",
                "displayname": "Whatsapp Bridge",
                "avatar_url": self.config["appservice.bot_avatar"],
            },
            "channel": {
                "id": str(self.phone_id),
                "displayname": None,
                "avatar_url": None,
            },
        }

    async def delete(self) -> None:
        """
        Delete a portal
        """
        await DBMessage.delete_all(self.mxid)
        self.log.warning(f"Deleting portal {self.mxid}")
        self.by_mxid.pop(self.mxid, None)
        self.by_phone_id.pop(self.phone_id, None)
        self.mxid = None
        await self.update()

    async def get_dm_puppet(self) -> Puppet | None:
        """
        Get the puppet of the user
        """
        if not self.is_direct:
            return None
        return await Puppet.get_by_phone_id(self.phone_id, app_business_id=self.app_business_id)

    async def save(self) -> None:
        """
        Update the information of the portal
        """
        await self.update()

    async def handle_whatsapp_message(
        self, source: User, message: WhatsappEvent, sender: WhatsappContacts
    ) -> None:
        """
        When a user of Whatsapp send a message, this function takes it and sends to Matrix

        Parameters
        ----------
        source : User
            The class that will be used to specify who receives the message.

        message : MessageEventContent
            The class that containt the data of the message.

        sender: WhatsappMessageSender
            The class that will be used to specify who send the message.

        Exceptions
        ----------
        Exception:
            Show and error if the media does not upload.
        """
        # Validate if the matrix room exists, if not, it is created
        if not await self.create_matrix_room(source=source, sender=sender):
            return

        has_been_sent: EventID | None = None
        message_data = message.entry.changes.value.messages

        if not message_data:
            self.log.error("No message data")
            return

        # Validate if the message exist and that the message has a reply
        whatsapp_message_type = message_data.type
        whatsapp_message_id = message_data.id
        file_name = ""
        media_id = None
        messasge_reply = {}

        if message_data.context and not whatsapp_message_type == "interactive":
            reply_message_id = message_data.context.id
            messasge_reply: DBMessage = await DBMessage.get_by_whatsapp_message_id(
                reply_message_id
            )

        # Validate what kind of message is and obtain the id of the message
        if whatsapp_message_type == "text":
            message_type = MessageType.TEXT
            attachment = message_data.text.body

        elif whatsapp_message_type == "image":
            message_type = MessageType.IMAGE
            media_id = message_data.image.id

        elif whatsapp_message_type == "video":
            message_type = MessageType.VIDEO
            media_id = message_data.video.id

        elif whatsapp_message_type == "audio":
            message_type = MessageType.AUDIO
            media_id = message_data.audio.id
            # This is to distinguish between a voice message and an audio message
            file_name = "Voice Audio" if message_data.audio.voice else "Audio"

        elif whatsapp_message_type == "sticker":
            message_type = MessageType.IMAGE
            media_id = message_data.sticker.id

        elif whatsapp_message_type == "document":
            message_type = MessageType.FILE
            media_id = message_data.document.id
            file_name = message_data.document.filename

        elif whatsapp_message_type == "location":
            message_type = MessageType.LOCATION

        elif whatsapp_message_type == "interactive":
            message_type = MessageType.TEXT
            if message_data.interactive.type == "button_reply":
                attachment = message_data.interactive.button_reply.title
            elif message_data.interactive.type == "list_reply":
                attachment = message_data.interactive.list_reply_message

        else:
            self.log.error(f"Unsupported message type: {whatsapp_message_type}")
            await self.az.intent.send_notice(self.mxid, "Error getting the message")
            return

        if message_type == MessageType.TEXT:
            content_attachment = TextMessageEventContent(msgtype=message_type, body=attachment)

        elif message_type != MessageType.LOCATION:
            if media_id:
                # Obtain the url of the file from Whatsapp API
                media_data = await self.whatsapp_client.get_media(media_id=media_id)

                if not media_data:
                    self.log.error("Error getting the data of the media")
                    await self.az.intent.send_notice(
                        self.mxid, "Error getting the data of the media"
                    )
                    return

                # Obtain the media file
                data = await media_data.read()

                try:
                    # Upload the message media to Matrix
                    attachment = await self.main_intent.upload_media(data=data)
                except Exception as e:
                    self.log.exception(f"Message not receive, error: {e}")
                    return

            # Create the content of the message media for send to Matrix
            content_attachment = MediaMessageEventContent(
                body=file_name,
                msgtype=message_type,
                url=attachment,
                info=FileInfo(size=len(data)),
            )

        else:
            # Obtain the dat of the location
            location = message_data.location
            longitude = location.longitude
            latitude = location.latitude
            long_direction = "E" if longitude > 0 else "W"
            lat_direction = "N" if latitude > 0 else "S"

            # Create the body of the location message
            body = (
                f"{location.name} - {round(abs(latitude), 4)}° {lat_direction}, "
                f"{round(abs(longitude), 4)}° {long_direction}"
            )

            # Create the url of the location message
            url = f"{self.openstreetmap_url}{latitude}/{longitude}"

            # create the content of the location message
            content_attachment = LocationMessageEventContent(
                body=f"{location.name} {location.address}",
                msgtype=message_type,
                geo_uri=f"geo:{latitude},{longitude}",
                external_url=f"{self.google_maps_url}?q={latitude},{longitude}",
            )

            content_attachment["format"] = str(Format.HTML)
            content_attachment["formatted_body"] = f"Location: <a href='{url}'>{body}</a>"

        has_been_sent = await self.send_data_message(
            content_attachment=content_attachment,
            messasge_reply=messasge_reply,
            message_type=message_type,
        )

        puppet: Puppet = await self.get_dm_puppet()

        # Save the message in the database
        msg = DBMessage(
            event_mxid=has_been_sent,
            room_id=self.mxid,
            phone_id=self.phone_id,
            sender=puppet.mxid,
            whatsapp_message_id=whatsapp_message_id,
            app_business_id=message.entry.id,
            created_at=datetime.now(),
        )
        await msg.insert()

    async def send_data_message(
        self, content_attachment: Any, messasge_reply: DBMessage, message_type: str
    ) -> EventID:
        """
        Obtain the data of the message that will be send to Matrix and validate if the message has
        a reply, if is it, the message is sent to Matrix with the reply message
        """
        if messasge_reply:
            # Create the content of the message media for send to Matrix
            content = await whatsapp_reply_to_matrix(
                content_attachment, messasge_reply, self.main_intent, self.log, message_type
            )

            content.external_url = content.external_url
            # Send the message to Matrix
            return await self.main_intent.send_message(self.mxid, content)

        else:
            # Send the message to Matrix
            return await self.main_intent.send_message(self.mxid, content_attachment)

    async def handle_whatsapp_read(self, message_id: WhatsappMessageID) -> None:
        """
        Send a read event to Matrix
        """
        if not self.mxid:
            self.log.error("No mxid, ignoring read")
            return

        async with self._send_lock:
            msg = await DBMessage.get_by_whatsapp_message_id(message_id)
            if msg:
                await self.main_intent.mark_read(self.mxid, msg.event_mxid)
            else:
                self.log.debug(f"Ignoring the null message")

    async def handle_whatsapp_reaction(
        self, reaction_event: WhatsappEvent, sender: WhatsappContacts
    ) -> None:
        """
        When a user of Whatsapp reaction to a message, this function takes it and sends its to Matrix

        Parameters
        ----------
        reaction_event : MetaReactionEvent
            The class that containt the data of the reaction.

        sender: WhatsappMessageSender
            The class that will be used to specify who send the reaction.
        """
        if not self.mxid:
            return

        async with self._send_lock:
            data_reaction: WhatsappReaction = reaction_event.entry.changes.value.messages.reaction
            msg_id = data_reaction.message_id
            msg = await DBMessage.get_by_whatsapp_message_id(whatsapp_message_id=msg_id)

            if msg:
                if not data_reaction.emoji:
                    reaction_to_remove = await DBReaction.get_by_whatsapp_message_id(
                        msg.whatsapp_message_id, sender
                    )

                    if reaction_to_remove:
                        await DBReaction.delete_by_event_mxid(
                            reaction_to_remove.event_mxid, self.mxid, sender
                        )
                        has_been_sent = await self.main_intent.redact(
                            self.mxid, reaction_to_remove.event_mxid
                        )
                    return
                else:
                    message_with_reaction = await DBReaction.get_by_whatsapp_message_id(
                        msg.whatsapp_message_id, sender
                    )

                    if message_with_reaction:
                        await DBReaction.delete_by_event_mxid(
                            message_with_reaction.event_mxid, self.mxid, sender
                        )
                        await self.main_intent.redact(self.mxid, message_with_reaction.event_mxid)

                    try:
                        has_been_sent = await self.main_intent.react(
                            self.mxid,
                            msg.event_mxid,
                            data_reaction.emoji,
                        )
                    except Exception as e:
                        self.log.exception(f"Error sending reaction: {e}")
                        await self.main_intent.send_notice(self.mxid, "Error sending reaction")
                        return

            else:
                self.log.error(f"Message id not found, mid: {msg_id}")
                return

            await DBReaction(
                event_mxid=has_been_sent,
                room_id=self.mxid,
                sender=sender,
                whatsapp_message_id=msg.whatsapp_message_id,
                reaction=data_reaction.emoji,
                created_at=datetime.now(),
            ).insert()

    async def handle_matrix_join(self, user: User) -> None:
        if self.is_direct or not await user.is_logged_in():
            return

    async def handle_matrix_message(
        self,
        sender: "User",
        message: MessageEventContent,
        event_id: EventID,
    ) -> None:
        """
        It takes a message from matrix and sends it to the Whatsapp API

        Parameters
        ----------
        sender : User
            The class that will be used to specify who sends the message.

        message : MessageEventContent
            The class that containts the data of the message.

        event_id: EventID
            The id of the event.

        Exceptions
        ----------
        FileExistsError:
            If the message is not sent, an error is raised.
        ClientConnectorError:
            If there is an error with the connection
        """
        if message.msgtype == "m.interactive_message":
            await self.handle_interactive_message(sender, message, event_id)
            return

        orig_sender = sender
        response = None
        aditional_data = {}
        sender, is_relay = await self.get_relay_sender(sender, f"message {event_id}")
        if is_relay:
            await self.apply_relay_message_format(orig_sender, message)

        if message.msgtype == MessageType.NOTICE and not self.config["bridge.bridge_notices"]:
            return

        if message.get_reply_to():
            reply_message: DBMessage = await DBMessage.get_by_mxid(
                message.get_reply_to(), self.mxid
            )
            if reply_message:
                aditional_data["reply_to"] = {"wb_message_id": reply_message.whatsapp_message_id}

        # If the message is a text message, we send the message to the Whatsapp API
        if message.msgtype in (MessageType.TEXT, MessageType.NOTICE):
            # If the format of the message is a HTML, we convert it to a valid format of Whatsapp
            if message.format == Format.HTML:
                text = await matrix_to_whatsapp(message.formatted_body)
            else:
                text = message.body

            try:
                # Send the message to Whatsapp
                response = await self.whatsapp_client.send_message(
                    message=text,
                    phone_id=self.phone_id,
                    message_type=message.msgtype,
                    aditional_data=aditional_data,
                )
            except TypeError as error:
                self.log.error(f"Error sending the message: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error sending the message")
                return
            except ClientConnectorError as error:
                self.log.error(f"Error with the connection: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error with the connection")
                return

        elif message.msgtype in (
            MessageType.IMAGE,
            MessageType.VIDEO,
            MessageType.AUDIO,
            MessageType.FILE,
        ):
            # We get the url of the media message. Message.url is something like mxc://xyz, so we
            # remove the first 6 characters to get the media hash
            media_mxc = message.url
            media_hash = media_mxc[6:]
            # We get the url of the media message
            url = f"{self.homeserver_address}/_matrix/media/r0/download/{media_hash}"

            # We send the media message to the Whatsapp API
            try:
                response = await self.whatsapp_client.send_message(
                    phone_id=self.phone_id,
                    message_type=message.msgtype,
                    url=url,
                    aditional_data=aditional_data,
                )
            except TypeError as error:
                self.log.error(f"Error sending the file: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error sending the file")
                return
            except ClientConnectorError as error:
                self.log.error(f"Error with the connection: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error with the connection")
                return

        elif message.msgtype == MessageType.LOCATION:
            # We get the directions of the location message and we send it to the Whatsapp API
            # A location message has a geo_uri like geo:37.786971,-122.399677 and we need to get
            # the latitude and longitude to send it to the Whatsapp API
            latitud = message.geo_uri.split(",")[0].split(":")[1]
            longitud = message.geo_uri.split(",")[1].split(";")[0]

            # We send the location message to the Whatsapp API
            try:
                response = await self.whatsapp_client.send_message(
                    phone_id=self.phone_id,
                    message_type=message.msgtype,
                    location=(latitud, longitud),
                    aditional_data=aditional_data,
                )
            except TypeError as error:
                self.log.error(f"Error sending the file: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error sending the location")
                return
            except ClientConnectorError as error:
                self.log.error(f"Error with the connection: {error}")
                await self.main_intent.send_notice(self.mxid, f"Error with the connection")
                return
            except ValueError as error:
                self.log.error(f"Error sending the location message: {error}")
                await self.main_intent.send_notice(
                    self.mxid, f"Error sending the location message"
                )
                return

        else:
            self.log.error(f"Ignoring unknown message {message}")
            return

        if not response:
            self.log.debug(f"Error sending message {message}")
            await self.main_intent.send_notice(self.mxid, "Error sending the message")
            return

        self.log.debug(f"Whatsapp send response: {response}")
        message_id = response.get("messages")[0].get("id")

        # Save the message in the database
        await DBMessage(
            event_mxid=event_id,
            room_id=self.mxid,
            phone_id=self.phone_id,
            sender=sender.mxid,
            whatsapp_message_id=WhatsappMessageID(message_id),
            app_business_id=self.app_business_id,
            created_at=datetime.now(),
        ).insert()

    async def handle_matrix_reaction(
        self,
        message: DBMessage,
        user: User,
        reaction: ReactionEventContent,
        event_id: EventID,
    ) -> None:
        """
        When a user of Matrix react to a message, this function takes it and sends it to Meta

        Parameters
        ----------

        message : DBMessage
            The class that containt the data of the message.

        sender: MetaMessageSender
            The class that will be used to specify who send the message.

        reaction: ReactionEventContent
            The class that containt the data of the reaction.
        """
        if not message.whatsapp_message_id:
            self.log.error(f"Message id not found, mid: {message.whatsapp_message_id}")
            return

        reaction_value = reaction.relates_to.key
        message_with_reaction = await DBReaction.get_by_whatsapp_message_id(
            message.whatsapp_message_id, user.mxid
        )

        if message_with_reaction:
            await DBReaction.delete_by_event_mxid(
                message_with_reaction.event_mxid, self.mxid, user.mxid
            )
            await self.main_intent.redact(self.mxid, message_with_reaction.event_mxid)

        try:
            await self.whatsapp_client.send_reaction(
                message_id=message.whatsapp_message_id,
                phone_id=message.phone_id,
                emoji=reaction_value,
            )
        except Exception as e:
            self.log.exception(f"Error sending reaction: {e}")
            self.main_intent.send_notice("Error sending reaction")
            return

        await DBReaction(
            event_mxid=event_id,
            room_id=self.mxid,
            sender=user.mxid,
            whatsapp_message_id=message.whatsapp_message_id,
            reaction=reaction_value,
            created_at=datetime.now(),
        ).insert()

    async def handle_matrix_unreact(
        self,
        message: DBMessage,
        user: User,
    ) -> None:
        """
        When a user of Matrix unreact to a message, this function takes it and sends it to Whatsapp

        Parameters
        ----------
        message : DBMessage
            The class that containt the data of the message.

        reaction: ReactionEventContent
            The class that containt the data of the reaction.
        """
        if not message.whatsapp_message_id:
            return

        try:
            await self.whatsapp_client.send_reaction(
                message_id=message.whatsapp_message_id,
                phone_id=message.phone_id,
                emoji="",
            )
        except Exception as e:
            self.log.exception(f"Error sending reaction: {e}")
            return

        await DBReaction.delete_by_event_mxid(message.event_mxid, self.mxid, user.mxid)

    async def handle_matrix_read(self) -> None:
        """
        Send a read event to Whatsapp

        Exceptions
        ClientConnectorError:
            Show and error if there is an error with the connection.
        AttributeError:
            Show and error if the message has an error.
        """
        puppet: Puppet = await Puppet.get_by_phone_id(self.phone_id, create=False)

        if not puppet:
            self.log.error("No puppet, ignoring read")
            return

        message: DBMessage = await DBMessage.get_last_message_puppet(self.mxid, puppet.custom_mxid)

        if not message:
            self.log.error("No message, ignoring read")
            return

        # We send the location message to the Whatsapp API
        try:
            response = await self.whatsapp_client.mark_read(message_id=message.whatsapp_message_id)
        except ClientConnectorError as error:
            self.log.error(f"Error sending the read event: {error}")
            return
        except AttributeError as error:
            self.log.error(f"Error with the message: {error}")
            return

        if response:
            self.log.debug(f"Whatsapp send response: {response}")
            return

    async def handle_matrix_template(
        self,
        sender: User,
        message: MessageEventContent,
        event_id: EventID,
        variables: Optional[list],
        template_name: str,
    ):
        """
        It sends the template to Whatsapp and save it in the database.

        Parameters
        ----------
        sender : User
            The class that will be used to specify who sends the message.
        message: str
            The message of the template.
        event_id: EventID
            The id of the event.
        variables:
            The variables of the template.
        template_name:
            The name of the template.

        Returns
        -------
            A dict with the response of the Whatsapp API.

        """
        try:
            # Send the message to Whatsapp
            response = await self.whatsapp_client.send_template(
                message=message,
                phone_id=self.phone_id,
                variables=variables,
                template_name=template_name,
            )
        except TypeError as error:
            self.log.error(f"Error sending the template: {error}")
            await self.main_intent.send_notice(self.mxid, f"Error sending the template: {error}")
            return 400, {"detail": f"Error sending the template: {error}"}
        except ClientConnectorError as error:
            self.log.error(f"Error with the connection: {error}")
            await self.main_intent.send_notice(
                self.mxid, f"Error trying to connect with Meta: {error}"
            )
            return 409, {"detail": f"Error sending the template: {error}"}
        except Exception as error:
            self.log.error(f"Error with the connection: {error}")
            await self.main_intent.send_notice(
                self.mxid, f"Error when try to send the template: {error}"
            )
            return 400, {"detail": f"Error sending the template: {error}"}

        # Save the template in the database
        await DBMessage(
            event_mxid=event_id,
            room_id=self.mxid,
            phone_id=self.phone_id,
            sender=sender.mxid,
            whatsapp_message_id=WhatsappMessageID(response.get("messages", [])[0].get("id", "")),
            app_business_id=self.app_business_id,
            created_at=datetime.now(),
        ).insert()

        return 200, {"detail": "The template has been sent successfully", "event_id": event_id}

    async def postinit(self) -> None:
        await self.init_whatsapp_client
        if self.mxid:
            self.by_mxid[self.mxid] = self

        if self.phone_id:
            self.by_phone_id[self.phone_id] = self

        if self.is_direct:
            puppet = await self.get_dm_puppet()
            self._main_intent = puppet.default_mxid_intent
        elif not self.is_direct:
            self._main_intent = self.az.intent

    @classmethod
    async def get_by_mxid(cls, mxid: RoomID) -> Optional["Portal"]:
        try:
            return cls.by_mxid[mxid]
        except KeyError:
            pass

        portal = cast(cls, await super().get_by_mxid(mxid))
        if portal is not None:
            await portal.postinit()
            return portal

        return None

    @classmethod
    async def get_by_phone_id(
        cls,
        phone_id: WhatsappPhone,
        *,
        app_business_id: WsBusinessID,
        create: bool = True,
    ) -> Optional["Portal"]:
        """
        Get a portal by its phone_id and save it in the cache

        Parameters
        ----------
        phone_id : WhatsappPhone
            The phone id of the user.

        app_business_id : WsBusinessID
            The business id of the user.

        create: bool
            Variable that indicates if the portal it will be create if not exist.
        """
        try:
            # Search if the phone_id is in the cache
            return cls.by_phone_id[phone_id]
        except KeyError:
            pass

        # Search if the phone_id is in the database
        portal = cast(cls, await super().get_by_phone_id(phone_id))
        if portal:
            await portal.postinit()
            return portal

        # If the phone_id is not in the database, it is created if the variable create is True
        if create:
            portal = cls(phone_id=phone_id, app_business_id=app_business_id)
            await portal.insert()
            await portal.postinit()
            return portal

        return None

    async def handle_whatsapp_error(self, message_error):
        """
        Send a message notification with the error that Whatsapp return

        Parameters
        ----------
        message_error : str
            The message error that whatsapp return.
        """
        await self.main_intent.send_notice(self.mxid, message_error)

    async def handle_interactive_message(
        self, sender: User, message: MessageEventContent, event_id: EventID
    ) -> None:
        """
        Handle the type of the interactive message and send it to Matrix

        Parameters
        ----------
        sender : User
            The class that will be used to specify who sends the message.
        message: MessageEventContent
            The class that containt the data of the message.
        event_id: EventID
            The id of the event.

        Exceptions
        ----------
        AttributeError:
            Show an atribute error if the message has a bad format.
        FileNotFoundError:
            Show an error if the message is not in the correct format.
        """
        message_body = None
        # Get the data of the interactive message
        event_interactive_message: EventInteractiveMessage = EventInteractiveMessage.from_dict(
            message
        )

        if not event_interactive_message.interactive_message:
            self.log.error("Error getting the interactive message")
            return

        # Whatsapp cloud can send a message with a header or without it
        header_type = None
        if event_interactive_message.interactive_message.header:
            header_type = event_interactive_message.interactive_message.header.type

        if header_type and header_type in ("image", "document", "video"):
            file_name = ""
            # Validate the type of the header media of the interactive message to send it to Matrix
            if header_type == "image":
                message_type = MessageType.IMAGE
                url = event_interactive_message.interactive_message.header.image.link
            elif header_type == "document":
                message_type = MessageType.FILE
                url = event_interactive_message.interactive_message.header.document.link
                file_name = event_interactive_message.interactive_message.header.document.filename
            elif header_type == "video":
                message_type = MessageType.VIDEO
                url = event_interactive_message.interactive_message.header.video.link

            if not url:
                self.log.error(
                    f"No url found when processing interactive message header {sender.mxid}"
                )
                await self.main_intent.send_notice(self.mxid, "Error getting the media url")
                return

            # Obtain the data of the message media
            response = await self.az.http_session.get(url)
            data = await response.read()

            try:
                # Upload the message media to Matrix
                attachment = await self.main_intent.upload_media(data=data)
            except Exception as e:
                self.log.exception(
                    f"Error uploading the media header of the interactive message: {e}"
                )
                return

            # Create the content of the message media for send to Matrix
            content_attachment = MediaMessageEventContent(
                body=file_name,
                msgtype=message_type,
                url=attachment,
                info=FileInfo(size=len(data)),
            )

            # Send message in matrix format
            await self.az.intent.send_message(self.mxid, content_attachment)

        # Obtain the body of the message to send it to matrix
        if event_interactive_message.interactive_message.type == "button":
            message_body = event_interactive_message.interactive_message.button_message
        elif event_interactive_message.interactive_message.type == "list":
            message_body = event_interactive_message.interactive_message.list_message

        try:
            msg = TextMessageEventContent(
                body=message_body,
                msgtype=MessageType.TEXT,
                formatted_body=markdown(message_body.replace("\n", "<br>")),
                format=Format.HTML,
            )
        except AttributeError as error:
            self.log.error(error)
            await self.main_intent.send_notice(
                self.mxid, f"Error sending the interactive message: {error}"
            )
            return

        msg.trim_reply_fallback()

        # Send message in matrix format
        await self.az.intent.send_message(self.mxid, msg)

        try:
            # Send the interactive message in whatsapp format
            response = await self.whatsapp_client.send_interactive_message(
                phone_id=self.phone_id,
                message_type="m.interactive_message",
                aditional_data=event_interactive_message.interactive_message.serialize(),
            )
        except TypeError as error:
            self.log.error(f"Error with the type of interactive message: {error}")
            await self.main_intent.send_notice(
                self.mxid, f"Error with the type of interactive message"
            )
            return
        except AttributeError as error:
            self.log.error(error)
            await self.main_intent.send_notice(self.mxid, f"Error getting an atribute: {error}")
            return
        except FileNotFoundError as error:
            self.log.error(error)
            await self.main_intent.send_notice(self.mxid, f"Error sending content: {error}")
            return
        except ClientConnectorError as error:
            self.log.error(f"Error with the connection: {error}")
            await self.main_intent.send_notice(self.mxid, f"Error with the connection")
            return
        except ValueError as error:
            self.log.error(f"Error sending the interactive message: {error}")
            await self.main_intent.send_notice(self.mxid, f"Error sending the interactive message")
            return

        # Save the message in the database
        await DBMessage(
            event_mxid=event_id,
            room_id=self.mxid,
            phone_id=self.phone_id,
            sender=sender.mxid,
            whatsapp_message_id=WhatsappMessageID(response.get("messages", [])[0].get("id", "")),
            app_business_id=self.app_business_id,
            created_at=datetime.now(),
        ).insert()
