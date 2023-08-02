from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

import asyncpg
from attr import dataclass
from mautrix.types import EventID, RoomID, UserID
from mautrix.util.async_db import Database

from meta.types import MetaMessageID

fake_db = Database.create("") if TYPE_CHECKING else None

log: logging.Logger = logging.getLogger("meta.out")


@dataclass
class Reaction:
    db: ClassVar[Database] = fake_db

    event_mxid: EventID
    room_id: RoomID
    sender: UserID
    meta_message_id: str
    reaction: str
    created_at: float = datetime.now()

    @property
    def _values(self):
        return (
            self.event_mxid,
            self.room_id,
            self.sender,
            self.meta_message_id,
            self.reaction,
            self.created_at,
        )

    async def insert(self) -> None:
        q = """
            INSERT INTO reaction (event_mxid, room_id, sender, meta_message_id, reaction, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self.db.execute(q, *self._values)

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Optional["Reaction"]:
        return cls(**row)

    @classmethod
    async def delete_all(cls, room_id: RoomID) -> None:
        await cls.db.execute("DELETE FROM reaction WHERE room_id=$1", room_id)

    @classmethod
    async def get_by_meta_message_id(
        cls, meta_message_id: MetaMessageID, sender: UserID
    ) -> Optional["Reaction"]:
        q = """
            SELECT event_mxid, room_id, sender, meta_message_id, reaction, created_at
            FROM reaction WHERE meta_message_id=$1 AND sender=$2
        """
        row = await cls.db.fetchrow(q, meta_message_id, sender)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_event_mxid(cls, event_mxid: EventID, room_id: RoomID) -> Optional["Reaction"]:
        q = """
            SELECT event_mxid, room_id, sender, meta_message_id, reaction, created_at
            FROM reaction WHERE event_mxid=$1 AND room_id=$2
        """
        row = await cls.db.fetchrow(q, event_mxid, room_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_last_reaction(cls, room_id: RoomID) -> "Reaction":
        q = """
            SELECT event_mxid, room_id, sender, meta_message_id, reaction, created_at
            FROM reaction WHERE room_id=$1 ORDER BY created_at DESC LIMIT 1
        """
        row = await cls.db.fetchrow(q, room_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def delete_by_event_mxid(
        cls, event_mxid: EventID, room_id: RoomID, sender: UserID
    ) -> "Reaction":
        q = """
            DELETE FROM reaction WHERE event_mxid=$1 AND room_id=$2 AND sender=$3
        """
        row = await cls.db.fetchrow(q, event_mxid, room_id, sender)
        if not row:
            return None
        return cls._from_row(row)
