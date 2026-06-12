from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from mautrix.appservice import AppService
from mautrix.bridge import BaseUser, async_getter_lock
from mautrix.types import RoomID, UserID

from whatsapp.types import WsBusinessID
from whatsapp_matrix.cache_manager import CacheManager

from . import portal as po
from . import puppet as pu
from .config import Config
from .db.user import User as DBUser

if TYPE_CHECKING:
    from .__main__ import WhatsappBridge


class User(DBUser, BaseUser):
    by_mxid: CacheManager
    by_business_id: CacheManager

    config: Config
    az: AppService
    loop: asyncio.AbstractEventLoop
    bridge: "WhatsappBridge"

    relay_whitelisted: bool
    is_admin: bool
    permission_level: str

    _sync_lock: asyncio.Lock
    _notice_room_lock: asyncio.Lock
    _connected: bool

    def __init__(
        self,
        mxid: UserID,
        app_business_id: str | None = None,
        notice_room: RoomID | None = None,
    ) -> None:
        super().__init__(mxid=mxid, app_business_id=app_business_id, notice_room=notice_room)
        BaseUser.__init__(self)
        self._notice_room_lock = asyncio.Lock()
        self._sync_lock = asyncio.Lock()
        self._connected = False
        perms = self.config.get_permissions(mxid)
        self.relay_whitelisted, self.is_whitelisted, self.is_admin, self.permission_level = perms

    @classmethod
    def init_cls(cls, bridge: "WhatsappBridge") -> None:
        cls.bridge = bridge
        cls.config = bridge.config
        cls.az = bridge.az
        cls.loop = bridge.loop
        # initialize TTL caches for users
        ttl = cls.config["cache.ttl"]
        maxsize = cls.config["cache.user_max_size"]
        cls.by_mxid = CacheManager(maxsize=maxsize, ttl=ttl, config=cls.config)
        cls.by_business_id = CacheManager(maxsize=maxsize, ttl=ttl, config=cls.config)

    async def get_portal_with(self, puppet: pu.Puppet, create: bool = True) -> po.Portal | None:
        return await po.Portal.get_by_puppet_and_business_id(
            puppet_id=puppet.id, app_business_id=self.app_business_id
        )

    async def is_logged_in(self) -> bool:
        return bool(self.app_business_id)

    async def get_puppet(self) -> pu.Puppet | None:
        if not self.mxid:
            return None
        return await pu.Puppet.get_by_mxid(self.mxid)

    def _add_to_cache(self) -> None:
        self.by_mxid[self.mxid] = self
        if self.app_business_id:
            self.by_business_id[self.app_business_id] = self

    @classmethod
    async def get_by_mxid(cls, mxid: UserID, create: bool = True) -> "User" | None:
        if pu.Puppet.get_id_from_mxid(mxid):
            return None

        user = cls.by_mxid.get_item(mxid)
        if user is not None:
            return user

        user = cast(cls, await super().get_by_mxid(mxid))
        if user is not None:
            user._add_to_cache()
            return user

        if create:
            user = cls(mxid)
            await user.insert()
            user._add_to_cache()
            return user

        return None

    @classmethod
    @async_getter_lock
    async def get_by_business_id(cls, business_id: WsBusinessID) -> "User" | None:

        user = cls.by_business_id.get_item(business_id)
        if user is not None:
            return user

        user = cast(cls, await super().get_by_business_id(business_id))
        if user is not None:
            user._add_to_cache()
            return user

        return None
