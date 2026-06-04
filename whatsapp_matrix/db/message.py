from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

import asyncpg
from attr import dataclass
from mautrix.types import EventID, UserID
from mautrix.util.async_db import Database

from whatsapp.types import WhatsappMessageID

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class Message:
    db: ClassVar[Database] = fake_db

    event_mxid: EventID
    sender: UserID
    whatsapp_message_id: str
    portal_id: int
    created_at: float

    @property
    def _values(self):
        return (
            self.event_mxid,
            self.sender,
            self.whatsapp_message_id,
            self.portal_id,
            self.created_at,
        )

    _columns = "event_mxid, sender, whatsapp_message_id, portal_id, created_at"

    async def insert(self) -> None:
        q = """
            INSERT INTO message (event_mxid, sender, whatsapp_message_id, portal_id, created_at)
            VALUES ($1, $2, $3, $4, $5)
        """
        await self.db.execute(q, *self._values)

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Optional["Message"]:
        return cls(**row)

    @classmethod
    async def delete_all(cls, portal_id: int) -> None:
        await cls.db.execute("DELETE FROM message WHERE portal_id=$1", portal_id)

    @classmethod
    async def get_by_whatsapp_message_id(
        cls, whatsapp_message_id: WhatsappMessageID
    ) -> Optional["Message"]:
        q = """
            SELECT event_mxid, sender, whatsapp_message_id, portal_id, created_at
            FROM message WHERE whatsapp_message_id=$1
        """
        row = await cls.db.fetchrow(q, whatsapp_message_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_mxid(cls, event_mxid: EventID) -> Optional["Message"]:
        q = """
            SELECT event_mxid, sender, whatsapp_message_id, portal_id, created_at
            FROM message WHERE event_mxid=$1
        """
        row = await cls.db.fetchrow(q, event_mxid)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_last_message(cls, portal_id: int) -> "Message":
        q = """
            SELECT event_mxid, sender, whatsapp_message_id, portal_id, created_at
            FROM message WHERE portal_id=$1 ORDER BY created_at DESC LIMIT 1
        """
        row = await cls.db.fetchrow(q, portal_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_last_message_puppet(cls, portal_id: int, sender: UserID) -> "Message":
        q = """
            SELECT event_mxid, sender, whatsapp_message_id, portal_id, created_at
            FROM message WHERE portal_id=$1 AND sender=$2 ORDER BY created_at DESC LIMIT 1
        """
        row = await cls.db.fetchrow(q, portal_id, sender)
        if not row:
            return None
        return cls._from_row(row)
