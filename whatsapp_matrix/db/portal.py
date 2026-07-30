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

    app_business_id: str
    mxid: RoomID | None
    relay_user_id: UserID | None
    phone_id: str | None = None
    bsuid: str | None = None
    puppet_id: int | None = None
    id: int | None = None

    @property
    def _values(self):
        return (
            self.phone_id,
            self.app_business_id,
            self.mxid,
            self.relay_user_id,
            self.bsuid,
            self.puppet_id,
        )

    _columns = "phone_id, app_business_id, mxid, relay_user_id, bsuid, puppet_id"

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> Portal:
        return cls(**row)

    async def insert(self) -> None:
        q = f"INSERT INTO portal ({self._columns}) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id"
        self.id = await self.db.fetchval(q, *self._values)

    async def update(self) -> None:
        q = """
            UPDATE portal
            SET phone_id=$1, app_business_id=$2, mxid=$3, relay_user_id=$4, bsuid=$5, puppet_id=$6
            WHERE (phone_id=$1 OR bsuid=$5) AND app_business_id=$2
        """
        await self.db.execute(q, *self._values)

    @classmethod
    async def get_by_phone_id(cls, phone_id: str, app_business_id: str) -> Optional["Portal"]:
        q = f"SELECT id, {cls._columns} FROM portal WHERE phone_id=$1 AND app_business_id=$2"
        row = await cls.db.fetchrow(q, phone_id, app_business_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_identifier(
        cls, phone_id: str, bsuid: str | None, app_business_id: str
    ) -> "Portal" | None:
        q = (
            f"SELECT id, {cls._columns} FROM portal WHERE (phone_id=$1 OR bsuid=$2)"
            " AND app_business_id=$3"
        )
        row = await cls.db.fetchrow(q, phone_id, bsuid, app_business_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_puppet_id_and_business_id(
        cls, puppet_id: str, app_business_id: str
    ) -> "Portal" | None:
        q = f"SELECT id, {cls._columns} FROM portal WHERE puppet_id=$1 AND app_business_id=$2"
        row = await cls.db.fetchrow(q, puppet_id, app_business_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_mxid(cls, mxid: RoomID) -> Optional["Portal"]:
        q = f"SELECT id, {cls._columns} FROM portal WHERE mxid=$1"
        row = await cls.db.fetchrow(q, mxid)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def all_with_room(cls) -> list[Portal]:
        q = f"SELECT id, {cls._columns} FROM portal WHERE mxid IS NOT NULL"
        rows = await cls.db.fetch(q)
        return [cls._from_row(row) for row in rows]
