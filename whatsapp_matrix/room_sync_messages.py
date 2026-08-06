import asyncio

from mautrix.types import RoomID


class RoomLock:
    """
    This class holds the synchronization primitives for a room, such as locks and events.
    It is used to manage the synchronization of the room initialization and the invitation
    of users to the room.
    """

    rooms_lock: dict[RoomID | tuple[str, str], asyncio.Lock] = {}

    def __init__(self, identifier: RoomID | tuple[str, str]):
        """
        Initialize the RoomLock class.

        Parameters
        ----------
        identifier : RoomID | tuple[str, str]
            The ID of the room or the tuple of phone_id or bsuid and app_business_id.

        """
        self.identifier = identifier
        self.primitive_type = asyncio.Lock

    def __enter__(self):
        return self.rooms_lock.setdefault(self.identifier, self.primitive_type())

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.rooms_lock.pop(self.identifier, None)
