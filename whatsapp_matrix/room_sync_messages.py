import asyncio

from mautrix.types import RoomID


class RoomSyncMessages:
    """
    This class holds the synchronization primitives for a room, such as locks and events.
    It is used to manage the synchronization of the room initialization and the invitation
    of users to the room.
    """

    room_sync_messages: dict[(RoomID, str), asyncio.Lock] = {}

    def __init__(self, room_id: RoomID, event_id: str):
        """
        Initialize the RoomSyncMessages class.

        Parameters
        ----------
        room_id : RoomID
            The ID of the room.

        event_id : str
            The ID of the event associated with the primitive, if applicable.

        """
        self.key = (room_id, event_id)
        self.primitive_type = asyncio.Lock

    def __enter__(self):
        if self.key in RoomSyncMessages.room_sync_messages:
            return RoomSyncMessages.room_sync_messages[self.key]

        RoomSyncMessages.room_sync_messages[self.key] = self.primitive_type()
        return RoomSyncMessages.room_sync_messages[self.key]

    def __exit__(self, exc_type, exc_val, exc_tb):
        RoomSyncMessages.room_sync_messages.pop(self.key, None)
