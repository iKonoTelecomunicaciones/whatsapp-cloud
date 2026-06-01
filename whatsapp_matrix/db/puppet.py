from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import asyncpg
from attr import dataclass
from mautrix.types import UserID
from mautrix.util.async_db import Database

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class Puppet:
    db: ClassVar[Database] = fake_db

    phone_id: str
    display_name: str | None
    custom_mxid: UserID | None
    username: str | None
    id: int | None = None

    @property
    def _values(self):
        return (
            self.phone_id,
            self.display_name,
            self.custom_mxid,
            self.username,
        )

    _columns = "phone_id, display_name, custom_mxid, username"

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Puppet:
        return cls(**row)

    async def insert(self) -> None:
        q = """
            INSERT INTO puppet (phone_id, display_name, custom_mxid, username)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        self.id = await self.db.fetchval(q, *self._values)

    async def update(self) -> None:
        q = """
            UPDATE puppet SET display_name=$2, custom_mxid=$3, username=$4
            WHERE phone_id=$1
        """
        await self.db.execute(q, *self._values)

    @classmethod
    async def get_by_phone_id(cls, phone_id: str) -> Puppet | None:
        q = """
            SELECT id, phone_id, display_name, custom_mxid, username
            FROM puppet WHERE phone_id=$1
        """
        row = await cls.db.fetchrow(q, phone_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_custom_mxid(cls, mxid: UserID) -> Puppet | None:
        q = """
            SELECT id, phone_id, display_name, custom_mxid, username
            FROM puppet WHERE custom_mxid=$1
        """
        row = await cls.db.fetchrow(q, mxid)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def all_with_custom_mxid(cls) -> list[Puppet]:
        q = """
            SELECT id, phone_id, display_name, custom_mxid, username
            FROM puppet WHERE custom_mxid IS NOT NULL
        """
        rows = await cls.db.fetch(q)
        return [cls._from_row(row) for row in rows]
