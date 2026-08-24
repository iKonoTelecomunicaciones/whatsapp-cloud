from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar, List, Optional

import asyncpg
from attr import dataclass
from mautrix.types import UserID
from mautrix.util.async_db import Database

from whatsapp.data import WsBusinessID, WSPhoneID
from whatsapp_matrix.util.crypto import decrypt_value, encrypt_value, is_encrypted

fake_db = Database.create("") if TYPE_CHECKING else None

PIN_PATTERN = re.compile(r"^\d{6}$")


@dataclass
class WhatsappApplication:
    db: ClassVar[Database] = fake_db
    encryption_key: ClassVar[bytes] = b""

    name: str
    admin_user: UserID
    business_id: WsBusinessID | None
    wb_phone_id: WSPhoneID | None
    page_access_token: str | None
    pin: str | None = None

    @property
    def _values(self):
        return (
            self.name,
            self.admin_user,
            self.business_id,
            self.page_access_token,
            self.wb_phone_id,
            self.pin,
        )

    _columns = "business_id, wb_phone_id, name, admin_user, page_access_token, pin"

    @classmethod
    def _encrypt_field(cls, value: str | None) -> str | None:
        if value is None or not cls.encryption_key:
            return value
        if is_encrypted(value):
            return value
        return encrypt_value(value, cls.encryption_key)

    @classmethod
    def _decrypt_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_encrypted(value):
            return value
        if not cls.encryption_key:
            raise ValueError("Encrypted value found but encryption key is not configured")
        return decrypt_value(value, cls.encryption_key)

    @classmethod
    def validate_pin(cls, pin: str) -> None:
        if not PIN_PATTERN.match(pin):
            raise ValueError("pin must be exactly 6 digits")

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> WhatsappApplication:
        data = dict(row)
        data["page_access_token"] = cls._decrypt_field(data.get("page_access_token"))
        data["pin"] = cls._decrypt_field(data.get("pin"))
        return cls(**data)

    @classmethod
    async def insert(
        cls,
        name: str,
        admin_user: str,
        business_id: WsBusinessID,
        wb_phone_id: WSPhoneID,
        page_access_token: str,
        pin: str | None = None,
    ) -> None:
        if pin is not None:
            cls.validate_pin(pin)

        encrypted_token = cls._encrypt_field(page_access_token)
        encrypted_pin = cls._encrypt_field(pin)
        q = f"INSERT INTO wb_application ({cls._columns}) VALUES ($1, $2, $3, $4, $5, $6)"
        await cls.db.execute(
            q, business_id, wb_phone_id, name, admin_user, encrypted_token, encrypted_pin
        )

    async def update(self) -> None:
        if self.pin is not None:
            self.validate_pin(self.pin)

        encrypted_token = self._encrypt_field(self.page_access_token)
        encrypted_pin = self._encrypt_field(self.pin)
        q = """
            UPDATE wb_application
            SET name=$2, page_access_token=$3, wb_phone_id=$4, pin=$5
            WHERE business_id=$1
        """
        await self.db.execute(
            q, self.business_id, self.name, encrypted_token, self.wb_phone_id, encrypted_pin
        )

    @classmethod
    async def update_all(
        cls,
        name: str,
        admin_user: str,
        business_id: WsBusinessID,
        wb_phone_id: WSPhoneID,
        page_access_token: str,
        pin: str | None = None,
    ) -> None:
        if pin is not None:
            cls.validate_pin(pin)
        encrypted_token = cls._encrypt_field(page_access_token)
        encrypted_pin = cls._encrypt_field(pin)
        q = """
            UPDATE wb_application
            SET name=$1, admin_user=$2, business_id=$3, wb_phone_id=$4, page_access_token=$5, pin=$6
            WHERE name=$1
        """
        await cls.db.execute(
            q, name, admin_user, business_id, wb_phone_id, encrypted_token, encrypted_pin
        )

    @classmethod
    async def update_by_admin_user(cls, user: str, values: tuple) -> None:
        """Update the app_name and page_access_token of whatsapp application using admin user."""
        app_name, access_token = values
        encrypted_token = cls._encrypt_field(access_token)
        q = """
            UPDATE wb_application
            SET name=$2, page_access_token=$3
            WHERE admin_user=$1
        """
        await cls.db.execute(q, user, app_name, encrypted_token)

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wb_application WHERE name=$1"
        row = await cls.db.fetchrow(q, name)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_business_id_and_phone_id(
        cls, business_id: WsBusinessID, phone_id: WSPhoneID
    ) -> WhatsappApplication | None:
        q = f"SELECT {cls._columns} FROM wb_application WHERE business_id=$1 AND wb_phone_id=$2"
        row = await cls.db.fetchrow(q, business_id, phone_id)

        if not row:
            return None

        return cls._from_row(row)

    @classmethod
    async def get_by_business_id(
        cls, business_id: WsBusinessID
    ) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wb_application WHERE business_id=$1"
        row = await cls.db.fetchrow(q, business_id)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_wb_phone_id(cls, wb_phone_id: WSPhoneID) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wb_application WHERE wb_phone_id=$1"
        row = await cls.db.fetchrow(q, wb_phone_id)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_admin_user(cls, admin_user: UserID) -> Optional["WhatsappApplication"]:
        q = f"SELECT {cls._columns} FROM wb_application WHERE admin_user=$1"
        row = await cls.db.fetchrow(q, admin_user)

        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_all_wb_apps(cls) -> List[WsBusinessID]:
        q = f"SELECT {cls._columns} FROM wb_application WHERE business_id IS NOT NULL"
        rows = await cls.db.fetch(q)

        if not rows:
            return []
        return [cls._from_row(gs_app).business_id for gs_app in rows]

    async def update_identifiers(
        self,
        updates: dict[str, str],
        old_business_id: WsBusinessID,
        old_wb_phone_id: WSPhoneID,
        current_business_id: WsBusinessID,
    ) -> bool:
        """
        Update the identifiers of the whatsapp application.

        Parameters
        ----------
        updates: dict[str, str]
            The updates to the whatsapp application.
        old_business_id: WsBusinessID
            The old business id of the whatsapp application.
        old_wb_phone_id: WSPhoneID
            The old wb phone id of the whatsapp application.
        current_business_id: WsBusinessID
            The current business id of the whatsapp application.

        Returns
        -------
        bool
            True if the business id caches should be invalidated, False otherwise.
        """
        invalidate_business_id_caches = False
        async with WhatsappApplication.db.acquire() as conn:
            async with conn.transaction():
                if "business_id" in updates and updates["business_id"] != old_business_id:
                    invalidate_business_id_caches = True
                    current_business_id = updates["business_id"]
                    await conn.execute(
                        "UPDATE wb_application SET business_id=$1 WHERE business_id=$2",
                        current_business_id,
                        old_business_id,
                    )

                set_parts: list[str] = []
                values: list[object] = [current_business_id]
                param_index = 2

                if "name" in updates:
                    set_parts.append(f"name=${param_index}")
                    values.append(updates["name"])
                    param_index += 1

                if "page_access_token" in updates:
                    set_parts.append(f"page_access_token=${param_index}")
                    values.append(WhatsappApplication._encrypt_field(updates["page_access_token"]))
                    param_index += 1

                if "wb_phone_id" in updates and updates["wb_phone_id"] != old_wb_phone_id:
                    set_parts.append(f"wb_phone_id=${param_index}")
                    values.append(updates["wb_phone_id"])
                    param_index += 1

                if set_parts:
                    await conn.execute(
                        f"UPDATE wb_application SET {', '.join(set_parts)} WHERE business_id=$1",
                        *values,
                    )

        return invalidate_business_id_caches
