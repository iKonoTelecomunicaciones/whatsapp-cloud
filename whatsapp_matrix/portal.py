from __future__ import annotations

from asyncio import Lock
from string import Template
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from mautrix.appservice import AppService, IntentAPI
from mautrix.bridge import BasePortal
from mautrix.types import (
    EventID,
    EventType,
    FileInfo,
    Format,
    MediaMessageEventContent,
    MessageEventContent,
    MessageType,
    PowerLevelStateEventContent,
    RoomID,
    TextMessageEventContent,
    UserID,
)

from whatsapp.api import WhatsappClient
from whatsapp.data import WhatsappContacts, WhatsappMessageEvent, WhatsappUserData
from whatsapp.types import WhatsappMessageID, WhatsappPhone, WsBusinessID
from whatsapp_matrix.formatter.from_matrix import matrix_to_whatsapp

from .db import Message as DBMessage
from .db import Portal as DBPortal
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
        self.whatsapp_client.ws_phone_id = whatsapp_app.ws_phone_id

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
        levels.events_default = 0
        levels.ban = 99
        levels.kick = 99
        levels.invite = 99
        levels.state_default = 0
        whatsapp_edit_level = 0
        levels.events[EventType.REACTION] = 0
        levels.events[EventType.ROOM_NAME] = whatsapp_edit_level
        levels.events[EventType.ROOM_AVATAR] = whatsapp_edit_level
        levels.events[EventType.ROOM_TOPIC] = whatsapp_edit_level
        levels.events[EventType.ROOM_ENCRYPTION] = 50 if self.matrix.e2ee else 99
        levels.events[EventType.ROOM_TOMBSTONE] = 99
        levels.users_default = 0
        # Remote delete is only for your own messages
        levels.redact = 99
        if self.main_intent.mxid not in levels.users:
            levels.users[self.main_intent.mxid] = 9001 if is_initial else 100
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
        self, source: User, message: WhatsappMessageEvent, sender: WhatsappContacts
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

        """
        # Validate if the matrix room exists, if not, it is created
        if not await self.create_matrix_room(source=source, sender=sender):
            return

        has_been_sent: EventID | None = None
        message_data = message.entry.changes.value.messages
        # Validate if the message exist and that the message has not a reply
        if message_data:
            whatsapp_message_type = message_data.type
            whatsapp_message_id = message_data.id

            # Validate if the message is a text message, if is it, the message is sent to the Whatsapp API
            if whatsapp_message_type == "text":
                message_text = message_data.text.body
                has_been_sent = await self.send_text_message(message_text)
            else:
                # Validate what kind of message is and obtain the id of the message
                if whatsapp_message_type == "image":
                    message_type = MessageType.IMAGE
                    media_id = message_data.image.id
                elif whatsapp_message_type == "video":
                    message_type = MessageType.VIDEO
                    media_id = message_data.video.id
                else:
                    self.log.error("Unsupported message type")
                    await self.az.intent.send_notice(self.mxid, "Error getting the message")
                    return

                # Obtain the url from Whatsapp API
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
                    attachment_url = await self.main_intent.upload_media(data=data)
                except Exception as e:
                    self.log.exception(f"Message not receive, error: {e}")
                    return

                # Create the content of the message media for send to Matrix
                content_attachment = MediaMessageEventContent(
                    body="",
                    msgtype=message_type,
                    url=attachment_url,
                    info=FileInfo(size=len(data)),
                )

                # Send the message to Matrix
                has_been_sent = await self.main_intent.send_message(self.mxid, content_attachment)

        puppet: Puppet = await self.get_dm_puppet()

        # Save the message in the database
        msg = DBMessage(
            event_mxid=has_been_sent,
            room_id=self.mxid,
            phone_id=self.phone_id,
            sender=puppet.mxid,
            whatsapp_message_id=whatsapp_message_id,
            app_business_id=message.entry.id,
        )
        await msg.insert()

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

        """

        orig_sender = sender
        sender, is_relay = await self.get_relay_sender(sender, f"message {event_id}")
        if is_relay:
            await self.apply_relay_message_format(orig_sender, message)

        if message.msgtype == MessageType.NOTICE and not self.config["bridge.bridge_notices"]:
            return

        # If the message is a text message, we send the message to the Whatsapp API
        if message.msgtype in (MessageType.TEXT, MessageType.NOTICE):
            # If the format of the message is a HTML, we convert it to a valid format of Whatsapp
            if message.format == Format.HTML:
                text = await matrix_to_whatsapp(message.formatted_body)
            else:
                text = text = message.body

            try:
                # Send the message to Whatsapp
                response = await self.whatsapp_client.send_message(
                    message=text,
                    phone_id=self.phone_id,
                    message_type=message.msgtype,
                )
            except FileNotFoundError as error:
                self.log.error(f"Error sending the message: {error}")
                error_message: str = error.args[0].get("error", {}).get("message", "")
                await self.main_intent.send_notice(
                    self.mxid, f"Error sending content: {error_message}"
                )
                return
        elif message.msgtype in (MessageType.IMAGE, MessageType.VIDEO):
            # We get the url of the media message. Message.url is something like mxc://xyz, so we
            # remove the first 6 characters to get the media hash
            media_mxc = message.url
            media_hash = media_mxc[6:]
            url = f"{self.homeserver_address}/_matrix/media/r0/download/{media_hash}"
            # We send the media message to the Whatsapp API
            try:
                response = await self.whatsapp_client.send_message(
                    phone_id=self.phone_id,
                    message_type=message.msgtype,
                    url=url,
                )
            except Exception as error:
                self.log.error(f"Error sending the attachment data: {error}")
                error_message = error.args[0].get("error", {}).get("message", "")
                await self.main_intent.send_notice(
                    self.mxid, f"Error sending content: {error_message}"
                )
                return

        else:
            self.log.error(f"Ignoring unknown message {message}")
            return

        if not response:
            self.log.debug(f"Error sending message {message}")
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
        ).insert()

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
