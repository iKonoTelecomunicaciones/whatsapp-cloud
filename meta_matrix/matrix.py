from __future__ import annotations

from typing import TYPE_CHECKING

from mautrix import bridge as br
from mautrix.bridge import BaseMatrixHandler, RejectMatrixInvite
from mautrix.types import (
    Event,
    EventID,
    EventType,
    ReactionEvent,
    ReactionEventContent,
    RedactionEvent,
    RoomID,
    SingleReceiptEventContent,
    UserID,
)

from .db import Message, Reaction
from .portal import Portal
from .user import User

if TYPE_CHECKING:
    from .__main__ import MetaBridge


class MatrixHandler(BaseMatrixHandler):
    def __init__(self, bridge: "MetaBridge") -> None:
        prefix, suffix = bridge.config["bridge.username_template"].format(userid=":").split(":")
        homeserver = bridge.config["homeserver.domain"]
        self.user_id_prefix = f"@{prefix}"
        self.user_id_suffix = f"{suffix}:{homeserver}"

        super().__init__(bridge=bridge)

    async def handle_leave(self, room_id: RoomID, user_id: UserID, event_id: EventID) -> None:
        portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        user = await User.get_by_mxid(user_id, create=False)
        if not user:
            return

        await portal.handle_matrix_leave(user)

    async def handle_event(self, evt: Event) -> None:
        if evt.type == EventType.ROOM_REDACTION:
            evt: RedactionEvent
            await self.handle_unreaction(evt.room_id, evt.sender, evt.event_id)

        elif evt.type == EventType.REACTION:
            evt: ReactionEvent
            await self.handle_reaction(evt.room_id, evt.sender, evt.content, evt.event_id)

    async def handle_invite(
        self, room_id: RoomID, user_id: UserID, inviter: User, event_id: EventID
    ) -> None:
        user = await User.get_by_mxid(user_id, create=False)
        if not user or not await user.is_logged_in():
            return
        portal = await Portal.get_by_mxid(room_id)
        if portal and not portal.is_direct:
            try:
                await portal.handle_matrix_invite(inviter, user)
            except RejectMatrixInvite as e:
                await portal.main_intent.send_notice(
                    portal.mxid, f"Failed to invite {user.mxid} on Gupshup: {e}"
                )

    async def send_welcome_message(self, room_id: RoomID, inviter: User) -> None:
        await super().send_welcome_message(room_id, inviter)
        if not inviter.notice_room:
            inviter.notice_room = room_id
            await inviter.update()
            await self.az.intent.send_notice(
                room_id, "This room has been marked as your Gupshup bridge notice room."
            )

    async def handle_join(self, room_id: RoomID, user_id: UserID, event_id: EventID) -> None:
        portal: Portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        user = await User.get_by_mxid(user_id, create=False)
        if not user:
            return

        await portal.handle_matrix_join(user)

    async def handle_read_receipt(
        self, user: User, portal: Portal, event_id: EventID, data: SingleReceiptEventContent
    ) -> None:
        await portal.handle_matrix_read_receipt(user, event_id)

    async def handle_unreaction(self, room_id: RoomID, user_id: UserID, event_id: EventID) -> None:
        """
        When a user of Matrix unreact to a message, this function takes the event and obtains with it
        the message to sends the unreact event to Meta.

        Parameters
        ----------
        room_id : RoomID
            The room where the reaction was sent.

        user_id : UserID
            The user that sent the reaction.

        reaction: ReactionEventContent
            The class that containt the data of the reaction.
        """
        self.log.debug(f"Received Matrix event {event_id} from {user_id} in {room_id}")
        self.log.trace("Event %s content: %s", event_id)
        user = await User.get_by_mxid(user_id)
        if not user:
            return

        portal = await Portal.get_by_mxid(room_id)
        if not portal:
            return

        last_reaction = await Reaction.get_last_reaction(room_id)
        message_id = last_reaction.meta_message_id
        message = await Message.get_by_meta_message_id(message_id)
        if not message:
            return

        await portal.handle_matrix_unreaction(message, user)

    async def handle_reaction(
        self, room_id: RoomID, user_id: UserID, reaction: ReactionEventContent, event_id: EventID
    ):
        """
        When a user of Matrix react to a message, this function takes the event and obtains with it
        the message to sends it to Meta.

        Parameters
        ----------
        room_id : RoomID
            The room where the reaction was sent.

        user_id : UserID
            The user that sent the reaction.

        reaction: ReactionEventContent
            The class that containt the data of the reaction.
        """
        self.log.debug(f"Received Matrix event {event_id} from {user_id} in {room_id}")
        self.log.trace("Event %s content: %s", event_id, reaction)
        message_id = reaction.relates_to.event_id
        self.log.error(f"userid: {self.config['bridge.username_template']}")
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

    async def allow_message(self, user: User) -> bool:
        return user.relay_whitelisted

    async def allow_bridging_message(self, user: User, portal: Portal) -> bool:
        return portal.has_relay or await user.is_logged_in()
