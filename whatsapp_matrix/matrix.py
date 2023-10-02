from __future__ import annotations

from typing import TYPE_CHECKING

from mautrix.bridge import BaseMatrixHandler, RejectMatrixInvite
from mautrix.types import (
    Event,
    EventID,
    EventType,
    ReactionEventContent,
    ReceiptEvent,
    RoomID,
    UserID,
)

from .db import Message, Reaction
from .portal import Portal
from .user import User

if TYPE_CHECKING:
    from .__main__ import WhatsappBridge


class MatrixHandler(BaseMatrixHandler):
    def __init__(self, bridge: "WhatsappBridge") -> None:
        prefix, suffix = bridge.config["bridge.username_template"].format(userid=":").split(":")
        homeserver = bridge.config["homeserver.domain"]
        self.user_id_prefix = f"@{prefix}"
        self.user_id_suffix = f"{suffix}:{homeserver}"

        super().__init__(bridge=bridge)

    async def handle_leave(self, room_id: RoomID, user_id: UserID, event_id: EventID) -> None:
        """
        Handle a matrix leave event.
        """
        # Search for the portal and the user
        portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        user = await User.get_by_mxid(user_id, create=False)
        if not user:
            return

        # We out the user from the portal
        await portal.handle_matrix_leave(user)

    async def handle_ephemeral_event(self, evt: ReceiptEvent) -> None:
        """
        Handle the ephemeral events, like reads, typing, etc.
        """
        self.log.debug(f"Received event: {evt}")
        # Validate that the event is a read event
        if evt.type == EventType.RECEIPT:
            room_id = evt.room_id
            portal: Portal = await Portal.get_by_mxid(room_id)
            if not portal:
                self.log.error("The read event can't be send because the portal does not exist")
                return

            # We send the read event to Whatsapp Api, for this we need the event id of the read
            # event, so we get the event id from the content of the read event
            event_id = ""
            for content in evt.content:
                event_id = content

            self.log.debug(f"Send read event: {evt}")
            await portal.handle_matrix_read(room_id=evt.room_id, event_id=event_id)
        return

    async def handle_event(self, evt: Event) -> None:
        if evt.type == EventType.ROOM_REDACTION:
            await self.handle_unreact(evt.room_id, evt.sender, evt.event_id, evt.redacts)

        elif evt.type == EventType.REACTION:
            await self.handle_reaction(evt.room_id, evt.sender, evt.content, evt.event_id)

    async def handle_invite(
        self, room_id: RoomID, user_id: UserID, inviter: User, event_id: EventID
    ) -> None:
        """
        Handle a matrix invite event.
        """
        # Search for the user, and the portal
        user = await User.get_by_mxid(user_id, create=False)
        if not user or not await user.is_logged_in():
            return
        portal = await Portal.get_by_mxid(room_id)
        if portal and not portal.is_direct:
            try:
                # We invite the user to the portal
                await portal.handle_matrix_invite(inviter, user)
            except RejectMatrixInvite as e:
                await portal.main_intent.send_notice(
                    portal.mxid, f"Failed to invite {user.mxid} on Whatsapp: {e}"
                )

    async def send_welcome_message(self, room_id: RoomID, inviter: User) -> None:
        await super().send_welcome_message(room_id, inviter)
        if not inviter.notice_room:
            inviter.notice_room = room_id
            await inviter.update()
            await self.az.intent.send_notice(
                room_id, "This room has been marked as your Whatsapp bridge notice room."
            )

    async def handle_join(self, room_id: RoomID, user_id: UserID, event_id: EventID) -> None:
        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        user = await User.get_by_mxid(user_id, create=False)
        if not user:
            return

        await portal.handle_matrix_join(user)

    async def allow_message(self, user: User) -> bool:
        return user.relay_whitelisted

    async def allow_bridging_message(self, user: User, portal: Portal) -> bool:
        return portal.has_relay or await user.is_logged_in()

    async def handle_reaction(
        self, room_id: RoomID, user_id: UserID, reaction: ReactionEventContent, event_id: EventID
    ):
        """
        When a user of Matrix react to a message, this function takes the event and obtains with it
        the message to sends it to Whatsapp.

        Parameters
        ----------
        room_id : RoomID
            The room where the reaction was sent.

        user_id : UserID
            The user that sent the reaction.

        reaction: ReactionEventContent
            The class that containt the data of the reaction.

        event_id: EventID
            The id of the event that contains the reaction.
        """
        self.log.debug(f"Received Matrix event {event_id} from {user_id} in {room_id}")
        self.log.trace("Event %s content: %s", event_id, reaction)
        message_id = reaction.relates_to.event_id
        user: User = await User.get_by_mxid(user_id)
        if not user:
            return

        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        message = await Message.get_by_mxid(message_id, room_id)

        if not message:
            self.log.error(f"No message found for {message_id}")
            return

        return await portal.handle_matrix_reaction(message, user, reaction, event_id)

    async def handle_unreact(
        self, room_id: RoomID, user_id: UserID, event_id: EventID, react_event_id: EventID
    ):
        """
        When a user of Matrix unreact to a message, this function takes the event and obtains with
        itthe message to sends the unreact event to Whatsapp.

        Parameters
        ----------
        room_id : RoomID
            The room where the reaction was sent.

        user_id : UserID
            The user that sent the reaction.

        event_id: EventID
            The event_id that was generated when the user unreacted.

        react_event_id: EventID
            The event_id of the message that was reacted.
        """
        self.log.debug(f"Received Matrix event {event_id} from {user_id} in {room_id}")
        self.log.trace("Event %s content: %s", event_id)
        user = await User.get_by_mxid(user_id)
        if not user:
            return

        portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        reacted_message = await Reaction.get_by_event_mxid(react_event_id, room_id)
        if not reacted_message:
            self.log.error(f"No message found for {react_event_id}")
            return

        message_id = reacted_message.whatsapp_message_id
        message = await Message.get_by_whatsapp_message_id(message_id)

        if not message:
            self.log.error(f"No message found for {message_id}")
            return

        await portal.handle_matrix_unreact(message, user)
