from __future__ import annotations

from typing import TYPE_CHECKING

from mautrix.bridge import BaseMatrixHandler, RejectMatrixInvite
from mautrix.types import (
    EventID,
    EventType,
    PresenceEvent,
    ReceiptEvent,
    RoomID,
    TypingEvent,
    UserID,
)

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
