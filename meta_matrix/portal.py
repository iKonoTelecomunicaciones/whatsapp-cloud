from __future__ import annotations

from asyncio import Lock
from string import Template
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from mautrix.appservice import AppService, IntentAPI
from mautrix.bridge import BasePortal
from mautrix.errors import MatrixError
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

from meta.api import MetaClient
from meta.data import MetaMessageEvent, MetaMessageSender, MetaStatusEvent
from meta.types import MetaMessageID, MetaPageID, MetaPsID
from meta_matrix.formatter.from_matrix import matrix_to_facebook

from .db import Message as DBMessage
from .db import MetaApplication as DBMetaApplication
from .db import Portal as DBPortal
from .formatter import facebook_reply_to_matrix, facebook_to_matrix
from .puppet import Puppet
from .user import User

if TYPE_CHECKING:
    from .__main__ import MetaBridge

StateBridge = EventType.find("m.bridge", EventType.Class.STATE)
StateHalfShotBridge = EventType.find("uk.half-shot.bridge", EventType.Class.STATE)

InviteList = Union[UserID, List[UserID]]


class Portal(DBPortal, BasePortal):
    by_mxid: Dict[RoomID, "Portal"] = {}
    by_ps_id: Dict[MetaPsID, "Portal"] = {}

    message_template: Template
    federate_rooms: bool
    invite_users: List[UserID]
    initial_state: Dict[str, Dict[str, Any]]
    auto_change_room_name: bool

    az: AppService
    private_chat_portal_meta: bool
    meta_client: MetaClient

    _main_intent: Optional[IntentAPI] | None
    _create_room_lock: Lock
    _send_lock: Lock

    def __init__(
        self,
        ps_id: str,
        app_page_id: str,
        room_id: Optional[RoomID] = None,
        relay_user_id: UserID | None = None,
    ) -> None:
        super().__init__(ps_id, app_page_id, room_id, relay_user_id)
        BasePortal.__init__(self)
        self._create_room_lock = Lock()
        self._send_lock = Lock()
        self.log = self.log.getChild(self.ps_id or self.room_id)
        self._main_intent = None
        self._relay_user = None
        self.error_codes = self.config["meta.error_codes"]
        self.homeserver_address = self.config["homeserver.public_address"]

    @property
    def main_intent(self) -> IntentAPI:
        if not self._main_intent:
            raise ValueError("Portal must be postinit()ed before main_intent can be used")
        return self._main_intent

    @property
    async def init_meta_client(self) -> Dict:
        try:
            meta_app = await DBMetaApplication.get_by_page_id(page_id=self.app_page_id)
        except Exception as e:
            self.log.exception(e)
            return

        self.meta_client.page_access_token = meta_app.page_access_token
        self.meta_client.page_id = meta_app.outgoing_page_id

    @property
    def is_direct(self) -> bool:
        return self.ps_id is not None

    @classmethod
    def init_cls(cls, bridge: "MetaBridge") -> None:
        cls.config = bridge.config
        cls.matrix = bridge.matrix
        cls.az = bridge.az
        cls.loop = bridge.loop
        BasePortal.bridge = bridge
        cls.private_chat_portal_meta = cls.config["bridge.private_chat_portal_meta"]
        cls.meta_client = bridge.meta_client

    def send_text_message(self, message: str) -> Optional[EventID]:
        html, text = facebook_to_matrix(message)
        content = TextMessageEventContent(msgtype=MessageType.TEXT, body=message)
        if html is not None:
            content.format = Format.HTML
            content.formatted_body = html
        return self.main_intent.send_message(self.room_id, content)

    async def create_matrix_room(
        self, source: User, sender: MetaMessageSender, app_origin: str
    ) -> RoomID:
        if self.room_id:
            return self.room_id
        async with self._create_room_lock:
            try:
                self.ps_id = sender.id
                return await self._create_matrix_room(
                    source=source, sender=sender, app_origin=app_origin
                )
            except Exception:
                self.log.exception("Failed to create portal")

    async def _create_matrix_room(
        self, source: User, sender: MetaMessageSender, app_origin: str
    ) -> RoomID:
        self.log.debug("Creating Matrix room")

        creator_info = await self.meta_client.get_user_data(sender.id)

        if not self.config["bridge.federate_rooms"]:
            creation_content["m.federate"] = False
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
        room_name_variables = {"userid": sender.id, "displayname": f"{creator_info.full_name}"}

        if app_origin == "page":
            room_name_template: str = self.config["bridge.facebook.room_name_template"]
        else:
            room_name_template: str = self.config["bridge.instagram.room_name_template"]
            room_name_variables["username"] = creator_info.username

        if not self.config["bridge.federate_rooms"]:
            creation_content["m.federate"] = False
        self.room_id = await self.main_intent.create_room(
            name=room_name_template.format(**room_name_variables),
            is_direct=self.is_direct,
            initial_state=initial_state,
            invitees=invites,
            topic="Meta private chat",
            creation_content=creation_content,
            # Make sure the power level event in initial_state is allowed
            # even if the server sends a default power level event before it.
            # TODO remove this if the spec is changed to require servers to
            #      use the power level event in initial_state
            power_level_override={"users": {self.main_intent.mxid: 9001}},
        )
        if not self.room_id:
            raise Exception("Failed to create room: no mxid returned")

        self.log.debug(self.ps_id)
        puppet: Puppet = await Puppet.get_by_ps_id(self.ps_id, app_page_id=self.app_page_id)
        puppet.display_name = f"User {self.ps_id}"
        await self.main_intent.invite_user(
            self.room_id, puppet.mxid, extra_content=self._get_invite_content(puppet)
        )
        if puppet:
            try:
                await puppet.intent.join_room_by_id(self.room_id)
            except MatrixError:
                self.log.debug(
                    "Failed to join custom puppet into newly created portal", exc_info=True
                )
        await self.update()
        meta_user_info = await self.meta_client.get_user_data(self.ps_id)
        await puppet.update_info(meta_user_info)
        self.log.debug(f"Matrix room created: {self.room_id}")
        self.by_mxid[self.room_id] = self
        return self.room_id

    async def handle_matrix_leave(self, user: User) -> None:
        if self.is_direct:
            self.log.info(f"{user.mxid} left private chat portal with {self.chat_id}")
            if f"{user.gs_app}-{user.phone}" == self.chat_id:
                self.log.info(
                    f"{user.mxid} was the recipient of this portal. Cleaning up and deleting..."
                )
                await self.cleanup_and_delete()
        else:
            self.log.debug(f"{user.mxid} left portal to {self.chat_id}")

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
        levels = levels or PowerLevelStateEventContent()
        levels.events_default = 0
        levels.ban = 99
        levels.kick = 99
        levels.invite = 99
        levels.state_default = 0
        meta_edit_level = 0
        levels.events[EventType.REACTION] = 0
        levels.events[EventType.ROOM_NAME] = meta_edit_level
        levels.events[EventType.ROOM_AVATAR] = meta_edit_level
        levels.events[EventType.ROOM_TOPIC] = meta_edit_level
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
        return f"com.github.meta://meta/{self.ps_id}"

    @property
    def bridge_info(self) -> Dict[str, Any]:
        return {
            "bridgebot": self.az.bot_mxid,
            "creator": self.main_intent.mxid,
            "protocol": {
                "id": "facebook",
                "displayname": "Meta Bridge",
                "avatar_url": self.config["appservice.bot_avatar"],
            },
            "channel": {
                "id": str(self.ps_id),
                "displayname": None,
                "avatar_url": None,
            },
        }

    async def delete(self) -> None:
        await DBMessage.delete_all(self.room_id)
        self.by_mxid.pop(self.room_id, None)
        self.room_id = None
        await self.update()

    async def get_dm_puppet(self) -> Puppet | None:
        if not self.is_direct:
            return None
        return await Puppet.get_by_ps_id(self.ps_id, app_page_id=self.app_page_id)

    async def save(self) -> None:
        await self.update()

    async def handle_meta_message(
        self, source: User, message: MetaMessageEvent, sender: MetaMessageSender
    ) -> None:
        """
        When a user of Meta send a message, this function takes it and sends it to Matrix

        Parameters
        ----------
        source : User
            The class that will be used to specify who receives the message.

        message : MessageEventContent
            The class that containt the data of the message.

        sender: MetaMessageSender
            The class that will be used to specify who send the message.

        """
        # Validate if the matrix room exists, if not, it is created
        if not await self.create_matrix_room(
            source=source, sender=sender, app_origin=message.object
        ):
            return

        has_been_sent: EventID | None = None
        # Validate if the message exist and that the message has not a reply
        if message.entry.messaging.message and not message.entry.messaging.message.reply_to:
            meta_message_type = message.entry.messaging.message.attachments.type

            # Validate if the message is a text message, if is it, the message is sent to the Meta API
            if not meta_message_type:
                message_text = message.entry.messaging.message.text
                has_been_sent = await self.send_text_message(message_text)
            else:
                message_type = ""
                # Obtain the data of the message media
                response = await self.az.http_session.get(
                    message.entry.messaging.message.attachments.payload.url
                )
                data = await response.read()

                try:
                    # Upload the message media to Matrix
                    attachment_url = await self.main_intent.upload_media(data=data)
                except Exception as e:
                    self.log.exception(f"Message not receive :: error {e}")
                    return

                message_type = (
                    MessageType.IMAGE
                    if meta_message_type == "image"
                    else MessageType.VIDEO
                    if meta_message_type == "video"
                    else MessageType.AUDIO
                    if meta_message_type == "audio"
                    else MessageType.FILE
                    if meta_message_type == "file"
                    else None
                )

                if not message_type:
                    raise Exception("Message type not found")

                # Create the content of the message media for send to Matrix
                content_attachment = MediaMessageEventContent(
                    body="",
                    msgtype=message_type,
                    url=attachment_url,
                    info=FileInfo(size=len(data)),
                )

                # Send the message to Matrix
                has_been_sent = await self.main_intent.send_message(
                    self.room_id, content_attachment
                )

        elif message.entry.messaging.message and message.entry.messaging.message.reply_to:
            mgs_id = message.entry.messaging.message.reply_to.mid
            meta_message_type = message.entry.messaging.message.attachments.type

            # Validate if the message is a text message, if is it, the message is sent to the Meta
            # API
            if not meta_message_type:
                body = message.entry.messaging.message.text
                message_type = MessageType.TEXT

            else:
                # Obtain the data of the message media
                response = await self.az.http_session.get(
                    message.entry.messaging.message.attachments.payload.url
                )
                data = await response.read()

                try:
                    # Upload the message media to Matrix
                    body = await self.main_intent.upload_media(data=data)
                except Exception as e:
                    self.log.exception(f"Message not receive :: error {e}")
                    return

                message_type = (
                    MessageType.IMAGE
                    if meta_message_type == "image"
                    else MessageType.AUDIO
                    if meta_message_type == "audio"
                    else MessageType.VIDEO
                    if meta_message_type == "video"
                    else MessageType.FILE
                    if meta_message_type == "file"
                    else None
                )

            # Obtain the message of the reply
            evt = await DBMessage.get_by_meta_message_id(meta_message_id=mgs_id)
            if evt:
                # Create the content of the message media for send to Matrix
                content = await facebook_reply_to_matrix(
                    body, evt, self.main_intent, self.log, message_type
                )

                content.external_url = content.external_url
                # Send the message to Matrix
                has_been_sent = await self.main_intent.send_message(self.room_id, content)
            else:
                # if the reply message does not exist, the message is sent as a normal message
                # Create the content of the message media for send to Matrix
                content_attachment = MediaMessageEventContent(
                    body="",
                    msgtype=message_type,
                    url=body,
                    info=FileInfo(size=len(data)),
                )

                # Send the message to Matrix
                has_been_sent = await self.main_intent.send_message(
                    self.room_id, content_attachment
                )

        puppet: Puppet = await self.get_dm_puppet()
        msg = DBMessage(
            event_mxid=has_been_sent,
            room_id=self.room_id,
            ps_id=self.ps_id,
            sender=puppet.mxid,
            meta_message_id=message.entry.messaging.message.mid,
            app_page_id=message.entry.id,
        )
        await msg.insert()

    async def handle_matrix_join(self, user: User) -> None:
        if self.is_direct or not await user.is_logged_in():
            return

    async def handle_meta_status(self, status_event: MetaStatusEvent) -> None:
        if not self.room_id:
            return

        async with self._send_lock:
            msg = await DBMessage.get_last_message(self.room_id)
            if status_event.entry.messaging.delivery:
                pass
            elif status_event.entry.messaging.read:
                if msg:
                    await self.main_intent.mark_read(self.room_id, msg.event_mxid)
                else:
                    self.log.debug(f"Ignoring the null message")

    async def handle_matrix_message(
        self,
        sender: "User",
        message: MessageEventContent,
        event_id: EventID,
    ) -> None:
        """
        It takes a message from matrix and sends it to the Meta API

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

        if message.get_reply_to():
            await DBMessage.get_by_mxid(message.get_reply_to(), self.room_id)

        if message.msgtype == MessageType.NOTICE and not self.config["bridge.bridge_notices"]:
            return

        # If the message is a text message, we send the message to the Meta API
        if message.msgtype in (MessageType.TEXT, MessageType.NOTICE):
            aditional_data = {}
            if message.format == Format.HTML:
                text = await matrix_to_facebook(message.formatted_body)
            else:
                text = text = message.body

            if message.get_reply_to():
                reply_message = await DBMessage.get_by_mxid(message.get_reply_to(), self.room_id)
                aditional_data["reply_to"] = {"mid": reply_message.meta_message_id}

            try:
                response = await self.meta_client.send_message(
                    message=text,
                    recipient_id=self.ps_id,
                    message_type=message.msgtype,
                    aditional_data=aditional_data,
                )
            except Exception as error:
                self.log.error(f"Error sending the message: {error}")
                await self.main_intent.send_notice(
                    self.room_id, f"Error sending content: {error_message}"
                )
                return
        # If the message is a media message, we send the url of the media message to the Meta API
        elif message.msgtype in (
            MessageType.AUDIO,
            MessageType.VIDEO,
            MessageType.IMAGE,
            MessageType.FILE,
        ):
            aditional_data = {}

            # If the message was reply to another message, we add the message id to the
            # reply_to field
            if message.get_reply_to():
                reply_message = await DBMessage.get_by_mxid(message.get_reply_to(), self.room_id)
                aditional_data["reply_to"] = {"mid": reply_message.meta_message_id}

            # We get the url of the media message. Message.url is something like mxc://xyz, so we
            # remove the first 6 characters to get the media hash
            media_mxc = message.url
            media_hash = media_mxc[6:]
            url = f"{self.homeserver_address}/_matrix/media/r0/download/{media_hash}"

            # We send the media message to the Meta API
            try:
                response = await self.meta_client.send_message(
                    message="",
                    recipient_id=self.ps_id,
                    message_type=message.msgtype,
                    aditional_data=aditional_data,
                    url=url,
                )
            except Exception as error:
                self.log.error(f"Error sending the attachment data: {error}")
                error_message = error.args[0].get("error", {}).get("message", "")
                await self.main_intent.send_notice(
                    self.room_id, f"Error sending content: {error_message}"
                )
                return

        else:
            self.log.debug(f"Ignoring unknown message {message}")
            return

        if not response:
            self.log.debug(f"Error sending message {message}")
            return

        self.log.debug(f"Meta send response: {response}")
        await DBMessage(
            event_mxid=event_id,
            room_id=self.room_id,
            ps_id=self.ps_id,
            sender=sender.mxid,
            meta_message_id=MetaMessageID(response.get("message_id")),
            app_page_id=self.app_page_id,
        ).insert()

    async def handle_matrix_read_receipt(self, user: User, event_id: EventID):
        await self.meta_client.send_read_receipt(self.ps_id)

    async def postinit(self) -> None:
        await self.init_meta_client
        if self.room_id:
            self.by_mxid[self.room_id] = self

        if self.ps_id:
            self.by_ps_id[self.ps_id] = self

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
    async def get_by_ps_id(
        cls, ps_id: MetaPsID, *, app_page_id: MetaPageID, create: bool = True
    ) -> Optional["Portal"]:
        try:
            return cls.by_ps_id[ps_id]
        except KeyError:
            pass

        portal = cast(cls, await super().get_by_ps_id(ps_id))
        if portal:
            await portal.postinit()
            return portal

        if create:
            portal = cls(ps_id, app_page_id)
            await portal.insert()
            await portal.postinit()
            return portal

        return None
