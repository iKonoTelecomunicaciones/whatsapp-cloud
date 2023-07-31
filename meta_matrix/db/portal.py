from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

import asyncpg
from attr import dataclass
from mautrix.types import RoomID, UserID
from mautrix.util.async_db import Database

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class Portal:
    db: ClassVar[Database] = fake_db

    ps_id: str
    app_page_id: str
    room_id: RoomID | None
    relay_user_id: UserID | None

    @property
    def _values(self):
        return (
            self.ps_id,
            self.app_page_id,
            self.room_id,
            self.relay_user_id,
        )

    # TODO: Implement this property in the methods to which it applies
    _columns = "ps_id, app_page_id, room_id, relay_user_id"

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Portal:
        return cls(**row)

    async def insert(self) -> None:
        q = """
            INSERT INTO portal (ps_id, app_page_id, room_id, relay_user_id)
            VALUES ($1, $2, $3, $4)
        """
        await self.db.execute(q, *self._values)

    async def update(self) -> None:
        q = """
            UPDATE portal
            SET ps_id=$1, app_page_id= $2, room_id=$3, relay_user_id=$4 WHERE ps_id=$1
        """
        await self.db.execute(q, *self._values)

    @classmethod
    async def get_by_ps_id(cls, ps_id: str) -> Optional["Portal"]:
        q = "SELECT ps_id, app_page_id, room_id, relay_user_id FROM portal WHERE ps_id=$1"
        row = await cls.db.fetchrow(q, ps_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_mxid(cls, room_id: RoomID) -> Optional["Portal"]:
        q = "SELECT ps_id, app_page_id, room_id, relay_user_id FROM portal WHERE room_id=$1"
        row = await cls.db.fetchrow(q, room_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def all_with_room(cls) -> list[Portal]:
        q = """
            SELECT ps_id, room_id, app_page_id, relay_user_id
            FROM portal WHERE room_id IS NOT NULL
        """
        rows = await cls.db.fetch(q)
        return [cls._from_row(row) for row in rows]
