import asyncio
from typing import Any

from mautrix.types import RoomID, UserID


class RoomLock:
    """
    This class holds the synchronization primitives for a room, such as locks and events.
    It is used to manage the synchronization of the room initialization and the invitation
    of users to the room.
    """

    room_sync_primitives: dict[Any, asyncio.Lock | asyncio.Event] = {}

    def __init__(
        self,
        room_id: RoomID,
        user_id: UserID | None = None,
        *,
        primitive_type: type[asyncio.Lock] | type[asyncio.Event] = asyncio.Lock,
    ):
        """
        Initialize the RoomLock class.

        Parameters
        ----------
        room_id : RoomID
            The ID of the room.

        user_id : UserID | None
            The ID of the user. Required when using asyncio.Event.

        primitive_type : type[asyncio.Lock] | type[asyncio.Event]
            The type of synchronization primitive to use. Defaults to asyncio.Lock.

        """
        self.user_id = user_id
        self.primitive_type = primitive_type
        if primitive_type is asyncio.Lock:
            self.key = room_id
        else:
            self.key = (room_id, user_id)

    def __enter__(self):
        return RoomLock.room_sync_primitives.setdefault(self.key, self.primitive_type())

    def __exit__(self, exc_type, exc_val, exc_tb):
        RoomLock.room_sync_messages.pop(self.room_id, None)
