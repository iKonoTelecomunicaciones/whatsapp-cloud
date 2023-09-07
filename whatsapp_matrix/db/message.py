from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Iterable, Optional

import asyncpg
from attr import dataclass
from mautrix.types import EventID, RoomID, UserID
from mautrix.util.async_db import Database

from whatsapp.types import WhatsappMessageID, WsBusinessID, WhatsappPhone

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class Message:
    db: ClassVar[Database] = fake_db

    event_mxid: EventID
    room_id: RoomID
    phone_id: WhatsappPhone
    sender: UserID
    whatsapp_message_id: str
    app_business_id: str
    created_at: float = datetime.now()

    @property
    def _values(self):
        return (
            self.event_mxid,
            self.room_id,
            self.phone_id,
            self.sender,
            self.whatsapp_message_id,
            self.app_business_id,
            self.created_at,
        )

    _columns = (
        "event_mxid, room_id, phone_id, sender, whatsapp_message_id, app_business_id, created_at"
    )

    async def insert(self) -> None:
        q = """
            INSERT INTO message (event_mxid, room_id, phone_id, sender,
            whatsapp_message_id, app_business_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await self.db.execute(q, *self._values)

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Optional["Message"]:
        return cls(**row)

    @classmethod
    async def delete_all(cls, room_id: RoomID) -> None:
        await cls.db.execute("DELETE FROM message WHERE room_id=$1", room_id)

    @classmethod
    async def get_all_by_app_business_id(cls, business_id: WsBusinessID) -> Iterable["Message"]:
        q = """
            SELECT event_mxid, room_id, phone_id, sender, whatsapp_message_id, app_business_id, created_at
            FROM message WHERE whatsapp_message_id=$1
        """
        rows = await cls.db.fetch(q, business_id)
        if not rows:
            return None
        return [cls._from_row(row) for row in rows]

    @classmethod
    async def get_by_whatsapp_message_id(
        cls, whatsapp_message_id: WhatsappMessageID
    ) -> Optional["Message"]:
        q = """
            SELECT event_mxid, room_id, phone_id, sender, whatsapp_message_id, app_business_id, created_at
            FROM message WHERE whatsapp_message_id=$1
        """
        row = await cls.db.fetchrow(q, whatsapp_message_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_mxid(cls, event_mxid: EventID, room_id: RoomID) -> Optional["Message"]:
        q = """
            SELECT event_mxid, room_id, phone_id, sender, whatsapp_message_id, app_business_id, created_at
            FROM message WHERE event_mxid=$1 AND room_id=$2
        """
        row = await cls.db.fetchrow(q, event_mxid, room_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_last_message(cls, room_id: RoomID) -> "Message":
        q = """
            SELECT event_mxid, room_id, phone_id, sender, whatsapp_message_id, app_business_id, created_at
            FROM message WHERE room_id=$1 ORDER BY created_at DESC LIMIT 1
        """
        row = await cls.db.fetchrow(q, room_id)
        if not row:
            return None
        return cls._from_row(row)
