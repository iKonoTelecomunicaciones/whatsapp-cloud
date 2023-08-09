from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, AsyncIterable, Awaitable, Dict, Optional, cast

from mautrix.appservice import IntentAPI
from mautrix.bridge import BasePuppet, async_getter_lock
from mautrix.types import SyncToken, UserID
from mautrix.util.simple_template import SimpleTemplate
from yarl import URL

from meta.data import FacebookUserData, InstagramUserData
from meta.types import MetaPageID, MetaPsID

from .config import Config
from .db import Puppet as DBPuppet

if TYPE_CHECKING:
    from .__main__ import MetaBridge
    from .portal import Portal


class Puppet(DBPuppet, BasePuppet):
    by_ps_id: Dict[MetaPsID, "Puppet"] = {}
    by_custom_mxid: dict[UserID, Puppet] = {}
    by_meta_origin: dict[str, Puppet] = {}
    hs_domain: str
    mxid_template: SimpleTemplate[str]

    config: Config

    default_mxid_intent: IntentAPI
    default_mxid: UserID

    def __init__(
        self,
        ps_id: MetaPsID,
        app_page_id: MetaPageID,
        meta_origin: str = None,
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

        self.default_mxid = self.get_mxid_from_ps_id(self.ps_id, meta_origin)
        self.custom_mxid = self.default_mxid
        self.default_mxid_intent = self.az.intent.user(self.default_mxid)

        self.intent = self._fresh_intent()

    @classmethod
    def init_cls(cls, bridge: "MetaBridge") -> AsyncIterable[Awaitable[None]]:
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
        cls.sync_with_custom_puppets = False

        cls.login_device_name = "Meta Bridge"
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

    async def update_info(self, info: FacebookUserData | InstagramUserData) -> None:
        update = False
        update = await self._update_name(info) or update
        if update:
            await self.update()

    @classmethod
    def _get_displayname(cls, info: FacebookUserData | InstagramUserData) -> str:
        variables = {"displayname": f"{info.full_name}", "userid": info.id}
        if isinstance(info, FacebookUserData):
            puppet_displayname: str = cls.config["bridge.facebook.displayname_template"]
        else:
            puppet_displayname: str = cls.config["bridge.instagram.displayname_template"]
            variables["username"] = info.username

        return puppet_displayname.format(**variables)

    async def _update_name(self, info: FacebookUserData) -> bool:
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
    def get_mxid_from_ps_id(cls, ps_id: MetaPsID, meta_origin: str = "") -> UserID:
        custom_mxid = f"{meta_origin}_{ps_id}"
        return UserID(cls.mxid_template.format_full(custom_mxid))

    async def get_displayname(self) -> str:
        return await self.intent.get_displayname(self.mxid)

    @classmethod
    @async_getter_lock
    async def get_by_ps_id(
        cls,
        ps_id: MetaPsID,
        *,
        app_page_id: MetaPageID = None,
        meta_origin: str = None,
        create: bool = True,
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
            puppet = cls(ps_id=ps_id, app_page_id=None, meta_origin=meta_origin)
            await puppet.insert()
            puppet._add_to_cache()
            return puppet

        return None

    @classmethod
    def get_ps_id_from_mxid(cls, mxid: UserID) -> MetaPsID | None:
        ps_id = None
        origin_with_psid = cls.mxid_template.parse(mxid)
        if origin_with_psid:
            split_psid = origin_with_psid.split("_")
            if len(split_psid) > 1:
                ps_id = split_psid[1]

        if not ps_id:
            return None
        return ps_id

    @classmethod
    async def get_by_mxid(cls, mxid: UserID, *, create: bool = True) -> Optional["Puppet"]:
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
    async def all_with_custom_mxid(cls) -> AsyncGenerator["Puppet", None]:
        puppets = await super().all_with_custom_mxid()
        puppet: cls
        for index, puppet in enumerate(puppets):
            try:
                yield cls.by_ps_id[puppet.ps_id]
            except KeyError:
                puppet._add_to_cache()
                yield puppet
