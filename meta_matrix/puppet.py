from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, AsyncIterable, Awaitable, Dict, Optional, cast

from mautrix.appservice import IntentAPI
from mautrix.bridge import BasePuppet, async_getter_lock
from mautrix.types import SyncToken, UserID
from mautrix.util.simple_template import SimpleTemplate
from yarl import URL

from meta.data import MetaMessageSender, MetaUserData
from meta.types import MetaPsID, MetaPageID

from .config import Config
from .db import Puppet as DBPuppet

if TYPE_CHECKING:
    from .__main__ import GupshupBridge
    from .portal import Portal


class Puppet(DBPuppet, BasePuppet):
    by_ps_id: Dict[MetaPsID, "Puppet"] = {}
    by_custom_mxid: dict[UserID, Puppet] = {}
    hs_domain: str
    mxid_template: SimpleTemplate[str]

    config: Config

    default_mxid_intent: IntentAPI
    default_mxid: UserID

    def __init__(
        self,
        ps_id: MetaPsID,
        app_page_id: MetaPageID,
        display_name: str | None = None,
        is_registered: bool = False,
        custom_mxid: UserID | None = None,
        access_token: str | None = None,
        next_batch: SyncToken | None = None,
        base_url: URL | None = None,
    ) -> None:
        super().__init__(
            ps_id=ps_id,
            app_page_id=app_page_id,
            display_name=display_name,
            is_registered=is_registered,
            custom_mxid=custom_mxid,
            access_token=access_token,
            next_batch=next_batch,
            base_url=base_url,
        )

        self.log = self.log.getChild(self.ps_id)

        self.default_mxid = self.get_mxid_from_ps_id(self.ps_id)
        self.custom_mxid = self.default_mxid
        self.default_mxid_intent = self.az.intent.user(self.default_mxid)

        self.intent = self._fresh_intent()

    @classmethod
    def init_cls(cls, bridge: "GupshupBridge") -> AsyncIterable[Awaitable[None]]:
        cls.config = bridge.config
        cls.loop = bridge.loop
        cls.mx = bridge.matrix
        cls.az = bridge.az
        cls.hs_domain = cls.config["homeserver.domain"]
        cls.mxid_template = SimpleTemplate(
            cls.config["bridge.username_template"],
            "userid",
            prefix="@",
            suffix=f":{cls.hs_domain}",
        )
        cls.sync_with_custom_puppets = cls.config["bridge.sync_with_custom_puppets"]

        cls.login_device_name = "Gupshup Bridge"
        return (puppet.try_start() async for puppet in cls.all_with_custom_mxid())

    def intent_for(self, portal: "Portal") -> IntentAPI:
        if portal.ps_id == self.ps_id:
            return self.default_mxid_intent
        return self.intent

    def _add_to_cache(self) -> None:
        if self.ps_id:
            self.by_ps_id[self.ps_id] = self
        if self.custom_mxid:
            self.by_custom_mxid[self.custom_mxid] = self

    @property
    def mxid(self) -> UserID:
        return UserID(self.mxid_template.format_full(self.ps_id))

    async def save(self) -> None:
        await self.update()

    async def update_info(self, info: MetaUserData) -> None:
        update = False
        update = await self._update_name(info) or update
        if update:
            await self.update()

    @classmethod
    def _get_displayname(cls, info: MetaUserData) -> str:
        return cls.config["bridge.displayname_template"].format(
            displayname=f"{info.first_name} {info.last_name}"
        )

    async def _update_name(self, info: MetaUserData) -> bool:
        name = self._get_displayname(info)
        if name != self.display_name:
            self.display_name = name
            try:
                await self.default_mxid_intent.set_displayname(self.display_name)
                self.name_set = True
            except Exception:
                self.log.exception("Failed to update displayname")
                self.name_set = False
            return True
        return False

    @classmethod
    def get_mxid_from_ps_id(cls, ps_id: MetaPsID) -> UserID:
        return UserID(cls.mxid_template.format_full(ps_id))

    async def get_displayname(self) -> str:
        return await self.intent.get_displayname(self.mxid)

    @classmethod
    @async_getter_lock
    async def get_by_ps_id(
        cls, ps_id: MetaPsID, *, app_page_id: MetaPageID = None, create: bool = True
    ) -> Optional["Puppet"]:
        try:
            return cls.by_ps_id[ps_id]
        except KeyError:
            pass

        puppet = cast(cls, await super().get_by_ps_id(ps_id))
        if puppet is not None:
            puppet._add_to_cache()
            return puppet

        if create:
            puppet = cls(ps_id, app_page_id)
            await puppet.insert()
            puppet._add_to_cache()
            return puppet

        return None

    @classmethod
    def get_ps_id_from_mxid(cls, mxid: UserID) -> MetaPsID | None:
        ps_id = cls.mxid_template.parse(mxid)
        if not ps_id:
            return None
        return ps_id

    @classmethod
    async def get_by_mxid(cls, mxid: UserID, create: bool = True) -> Optional["Puppet"]:
        ps_id = cls.get_ps_id_from_mxid(mxid)
        if ps_id:
            return await cls.get_by_ps_id(ps_id, create=create)
        return None

    @classmethod
    @async_getter_lock
    async def get_by_custom_mxid(cls, mxid: UserID) -> "Puppet" | None:
        try:
            return cls.by_custom_mxid[mxid]
        except KeyError:
            pass

        puppet = cast(cls, await super().get_by_custom_mxid(mxid))
        if puppet:
            puppet._add_to_cache()
            return puppet

        return None

    @classmethod
    def get_id_from_mxid(cls, mxid: UserID) -> int | None:
        return cls.mxid_template.parse(mxid)

    @classmethod
    def get_mxid_from_ps_id(cls, ps_id: str) -> UserID:
        return UserID(cls.mxid_template.format_full(ps_id))

    @classmethod
    async def all_with_custom_mxid(cls) -> AsyncGenerator["Puppet", None]:
        puppets = await super().all_with_custom_mxid()
        puppet: cls
        for index, puppet in enumerate(puppets):
            try:
                yield cls.by_ps_id[puppet.ps_id]
            except KeyError:
                puppet._add_to_cache()
                yield puppet
