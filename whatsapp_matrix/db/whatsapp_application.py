from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, List, Optional

import asyncpg
from attr import dataclass
from mautrix.types import UserID
from mautrix.util.async_db import Database

from whatsapp.data import WsBusinessID, WSPhoneID

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class WhatsappApplication:
    db: ClassVar[Database] = fake_db

    name: str
    admin_user: UserID
    business_id: WsBusinessID | None
    wc_phone_id: WSPhoneID | None
    page_access_token: str | None

    @property
    def _values(self):
        return (
            self.name,
            self.admin_user,
            self.business_id,
            self.page_access_token,
            self.wc_phone_id,
        )

    _columns = "business_id, wc_phone_id, name, admin_user, page_access_token"

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> WhatsappApplication:
        return cls(**row)

    @classmethod
    async def insert(
        cls,
        name: str,
        admin_user: str,
        business_id: WsBusinessID,
        wc_phone_id: WSPhoneID,
        page_access_token: str,
    ) -> None:
        q = f"INSERT INTO wc_application ({cls._columns}) VALUES ($1, $2, $3, $4, $5)"
        await cls.db.execute(q, name, admin_user, business_id, wc_phone_id, page_access_token)

    @classmethod
    async def update(
        cls,
        name: str,
        admin_user: str,
        business_id: WsBusinessID,
        wc_phone_id: WSPhoneID,
        page_access_token: str,
    ) -> None:
        q = """
            UPDATE wc_application
            SET name=$1, admin_user=$2, business_id=$3, wc_phone_id=$4 ,page_access_token=$5 WHERE name=$1
        """
        await cls.db.execute(q, name, admin_user, business_id, wc_phone_id, page_access_token)

    @classmethod
    async def update_by_admin_user(cls, user: str, values: dict) -> None:
        """Update the app_name and page_access_token of whatsapp application using admin user."""
        q = """
            UPDATE wc_application
            SET name=$2, page_access_token=$3
            WHERE admin_user=$1
        """
        await cls.db.execute(q, user, *values)

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wc_application WHERE name=$1"
        row = await cls.db.fetchrow(q, name)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_business_id(
        cls, business_id: WsBusinessID
    ) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wc_application WHERE business_id=$1"
        row = await cls.db.fetchrow(q, business_id)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_wc_phone_id(cls, wc_phone_id: WSPhoneID) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wc_application WHERE wc_phone_id=$1"
        row = await cls.db.fetchrow(q, wc_phone_id)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_admin_user(cls, admin_user: UserID) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wc_application WHERE admin_user=$1"
        row = await cls.db.fetchrow(q, admin_user)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_all_wc_apps(cls) -> List[WsBusinessID]:
        q = f"SELECT {cls._columns} FROM wc_application WHERE business_id IS NOT NULL"
        rows = await cls.db.fetch(q)

        if not rows:
            return []
        return [cls._from_row(gs_app).business_id for gs_app in rows]
