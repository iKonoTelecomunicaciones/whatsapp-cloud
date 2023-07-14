from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, List, Optional

import asyncpg
from attr import dataclass
from mautrix.types import UserID
from mautrix.util.async_db import Database

from meta.data import MetaPageID

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class MetaApplication:
    db: ClassVar[Database] = fake_db

    name: str
    admin_user: UserID
    page_id: str | None
    page_access_token: str | None

    @property
    def _values(self):
        return (
            self.name,
            self.admin_user,
            self.page_id,
            self.page_access_token,
        )

    @classmethod
    def _from_row(cls, row: asyncpg.Record) -> MetaApplication:
        return cls(**row)

    @classmethod
    async def insert(
        cls,
        name: str,
        admin_user: str,
        page_id: str,
        verification_token: str,
        page_access_token: str,
    ) -> None:
        q = """
            INSERT INTO meta_application (name, admin_user, page_id, page_acces_token)
            VALUES ($1, $2, $3, $4)
        """
        await cls.db.execute(q, name, admin_user, page_id, verification_token, page_access_token)

    @classmethod
    async def update(
        cls,
        name: str,
        admin_user: str,
        page_id: str,
        verification_token: str,
        page_access_token: str,
    ) -> None:
        q = """
            UPDATE meta_application
            SET name=$1, admin_user=$2, page_id=$3, page_access_token=$4 WHERE name=$1
        """
        await cls.db.execute(q, name, admin_user, page_id, verification_token, page_access_token)

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["MetaApplication"]:
        q = """
            SELECT name, admin_user, page_id, page_access_token
            FROM meta_application WHERE name=$1
        """
        row = await cls.db.fetchrow(q, name)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_page_id(cls, page_id: str) -> Optional["MetaApplication"]:
        q = """
            SELECT name, admin_user, page_id, page_access_token
            FROM meta_application WHERE page_id=$1
        """
        row = await cls.db.fetchrow(q, page_id)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_by_admin_user(cls, admin_user: str) -> Optional["MetaApplication"]:
        q = """
            SELECT name, admin_user, page_id, page_access_token
            FROM meta_application WHERE admin_user=$1
        """
        row = await cls.db.fetchrow(q, admin_user)
        if not row:
            return None
        return cls._from_row(row)

    @classmethod
    async def get_all_meta_apps(cls) -> List[MetaPageID]:
        q = """
            SELECT name, admin_user, page_id, page_access_token
            FROM meta_application WHERE page_id IS NOT NULL
        """
        rows = await cls.db.fetch(q)
        if not rows:
            return []

        return [cls._from_row(gs_app).page_id for gs_app in rows]