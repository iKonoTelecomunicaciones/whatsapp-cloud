import asyncio

from mautrix.types import RoomID


class RoomLock:
    """
    This class holds the synchronization primitives for a room, such as locks and events.
    It is used to manage the synchronization of the room initialization and the invitation
    of users to the room.
    """

    rooms_lock: dict[RoomID, asyncio.Lock] = {}

    def __init__(self, room_id: RoomID):
        """
        Initialize the RoomLock class.

        Parameters
        ----------
        room_id : RoomID
            The ID of the room.

        """
        self.room_id = room_id
        self.primitive_type = asyncio.Lock

    def __enter__(self):
        return self.rooms_lock.setdefault(self.room_id, self.primitive_type())

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rooms_lock.pop(self.room_id, None)
