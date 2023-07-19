from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional

import asyncpg
from attr import dataclass
from mautrix.types import EventID, RoomID, UserID
from mautrix.util.async_db import Database

from meta.types import MetaMessageID, MetaPageID, MetaPsID

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class Message:
    db: ClassVar[Database] = fake_db

    event_mxid: EventID
    room_id: RoomID
    ps_id: MetaPsID
    sender: UserID
    meta_message_id: str
    app_page_id: str
    created_at: float = datetime.now()

    @property
    def _values(self):
        return (
            self.event_mxid,
            self.room_id,
            self.ps_id,
            self.sender,
            self.meta_message_id,
            self.app_page_id,
            self.created_at,
        )

    async def insert(self) -> None:
        q = """
            INSERT INTO message (event_mxid, room_id, ps_id, sender,
            meta_message_id, app_page_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await self.db.execute(q, *self._values)

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Optional["Message"]:
        return cls(**row)

    @classmethod
    async def delete_all(cls, room_id: RoomID) -> None:
        await cls.db.execute("DELETE FROM message WHERE room_id=$1", room_id)

    @classmethod
    async def get_all_by_app_page_id(cls, page_id: MetaPageID) -> Iterable["Message"]:
        q = """
            SELECT event_mxid, room_id, ps_id, sender, meta_message_id, app_page_id, created_at
            FROM message WHERE meta_message_id=$1
        """
        rows = await cls.db.fetch(q, page_id)
        if not rows:
            return None
        return [cls._from_row(row) for row in rows]

    @classmethod
    async def get_by_meta_message_id(cls, meta_message_id: MetaMessageID) -> Optional["Message"]:
        q = """
            SELECT event_mxid, room_id, ps_id, sender, meta_message_id, app_page_id, created_at
            FROM message WHERE meta_message_id=$1
        """
        row = await cls.db.fetchrow(q, meta_message_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_mxid(cls, event_mxid: EventID, room_id: RoomID) -> Optional["Message"]:
        q = """
            SELECT event_mxid, room_id, ps_id, sender, meta_message_id, app_page_id, created_at
            FROM message WHERE event_mxid=$1 AND room_id=$2
        """
        row = await cls.db.fetchrow(q, event_mxid, room_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_last_message(cls, room_id: RoomID) -> "Message":
        q = """
            SELECT event_mxid, room_id, ps_id, sender, meta_message_id, app_page_id, created_at
            FROM message WHERE room_id=$1 ORDER BY created_at DESC LIMIT 1
        """
        row = await cls.db.fetchrow(q, room_id)
        if not row:
            return None
        return cls._from_row(row)
