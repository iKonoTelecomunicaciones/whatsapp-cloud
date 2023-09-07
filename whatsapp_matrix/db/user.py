from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from attr import dataclass
from mautrix.types import RoomID, UserID
from mautrix.util.async_db import Database

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class User:
    db: ClassVar[Database] = fake_db

    mxid: UserID
    app_business_id: str | None
    notice_room: RoomID | None

    @property
    def _values(self):
        return (
            self.mxid,
            self.app_business_id,
            self.notice_room,
        )

    _columns = "mxid, app_business_id, notice_room"

    async def insert(self) -> None:
        q = f"INSERT INTO matrix_user ({self._columns}) VALUES ($1, $2, $3)"
        await self.db.execute(q, *self._values)

    async def update(self) -> None:
        q = "UPDATE matrix_user SET app_business_id=$1, notice_room=$2 WHERE mxid=$3"
        await self.db.execute(q, self.app_business_id, self.notice_room, self.mxid)

    @classmethod
    async def get_by_mxid(cls, mxid: UserID) -> User | None:
        q = f"SELECT {cls._columns} FROM matrix_user WHERE mxid=$1"
        row = await cls.db.fetchrow(q, mxid)
        if not row:
            return None
        return cls(**row)

    @classmethod
    async def get_by_business_id(cls, app_business_id: str) -> User | None:
        q = f"SELECT {cls._columns} FROM matrix_user WHERE app_business_id=$1"
        row = await cls.db.fetchrow(q, app_business_id)
        if not row:
            return None
        return cls(**row)

    @classmethod
    async def get_by_whatsapp_app(cls, whatsapp_app: str) -> User | None:
        q = f"SELECT {cls._columns} FROM matrix_user WHERE whatsapp_app=$1"
        row = await cls.db.fetchrow(q, whatsapp_app)
        if not row:
            return None
        return cls(**row)

    @classmethod
    async def all_logged_in(cls) -> list[User]:
        q = f"SELECT {cls._columns} FROM matrix_user WHERE app_business_id IS NOT NULL"
        rows = await cls.db.fetch(q)
        return [cls(**row) for row in rows]
