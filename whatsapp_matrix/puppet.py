from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, AsyncIterable, Awaitable, Dict, Optional, cast

from mautrix.appservice import IntentAPI
from mautrix.bridge import BasePuppet, async_getter_lock
from mautrix.types import SyncToken, UserID
from mautrix.util.simple_template import SimpleTemplate
from yarl import URL

from whatsapp.types import WsBusinessID, WhatsappPhone

from .config import Config
from .db import Puppet as DBPuppet

if TYPE_CHECKING:
    from .__main__ import WhatsappBridge
    from .portal import Portal


class Puppet(DBPuppet, BasePuppet):
    by_phone_id: Dict[WhatsappPhone, "Puppet"] = {}
    by_custom_mxid: dict[UserID, Puppet] = {}
    hs_domain: str
    mxid_template: SimpleTemplate[str]

    config: Config

    default_mxid_intent: IntentAPI
    default_mxid: UserID

    def __init__(
        self,
        phone_id: WhatsappPhone,
        app_business_id: WsBusinessID,
        display_name: str | None = None,
        is_registered: bool = False,
        custom_mxid: UserID | None = None,
        access_token: str | None = None,
        next_batch: SyncToken | None = None,
        base_url: URL | None = None,
    ) -> None:
        super().__init__(
            phone_id=phone_id,
            app_business_id=app_business_id,
            display_name=display_name,
            is_registered=is_registered,
            custom_mxid=custom_mxid,
            access_token=access_token,
            next_batch=next_batch,
            base_url=base_url,
        )

        self.log = self.log.getChild(self.phone_id)

        self.default_mxid = self.get_mxid_from_phone_id(self.phone_id)
        self.custom_mxid = self.default_mxid
        self.default_mxid_intent = self.az.intent.user(self.default_mxid)

        self.intent = self._fresh_intent()

    @classmethod
    def init_cls(cls, bridge: "WhatsappBridge") -> AsyncIterable[Awaitable[None]]:
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

        cls.login_device_name = "Whatsapp Bridge"
        return (puppet.try_start() async for puppet in cls.all_with_custom_mxid())

    def intent_for(self, portal: "Portal") -> IntentAPI:
        if portal.phone_id == self.phone_id:
            return self.default_mxid_intent
        return self.intent

    def _add_to_cache(self) -> None:
        if self.phone_id:
            self.by_phone_id[self.phone_id] = self
        if self.custom_mxid:
            self.by_custom_mxid[self.custom_mxid] = self

    @property
    def mxid(self) -> UserID:
        return UserID(self.mxid_template.format_full(self.phone_id))

    async def save(self) -> None:
        await self.update()

    async def update_info(self, info: Dict) -> None:
        update = False
        update = await self._update_name(info) or update
        if update:
            await self.update()

    @classmethod
    def _get_displayname(cls, info: Dict) -> str:
        """
        Get the name of the user to use on the matrix room.

        Parameters
        ----------
        info : Dict
            The name of the user and his phone id.
        """
        variables = {"displayname": f"{info.profile.name}", "userid": info.wa_id}
        puppet_displayname: str = cls.config["bridge.whatsapp_cloud.displayname_template"]

        return puppet_displayname.format(**variables)

    async def _update_name(self, info: Dict) -> bool:
        """
        Update the name of the user.

        Parameters
        ----------
        info : Dict
            The name of the user and his phone id.
        """
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
    def get_mxid_from_phone_id(cls, phone_id: WhatsappPhone) -> UserID:
        return UserID(cls.mxid_template.format_full(phone_id))

    async def get_displayname(self) -> str:
        return await self.intent.get_displayname(self.mxid)

    @classmethod
    @async_getter_lock
    async def get_by_phone_id(
        cls,
        phone_id: WhatsappPhone,
        *,
        app_business_id: WsBusinessID = None,
        create: bool = True,
    ) -> Optional["Puppet"]:
        """
        Get the puppet using the phone id.

        Parameters
        ----------
        phone_id : WhatsappPhone
            The phone id of the user.

        app_business_id : WsBusinessID
            The business_id of the whatsapp business account.

        create : bool
            The value to create the puppet if it doesn't exist.
        """
        try:
            # Search for the puppet in the cache
            return cls.by_phone_id[phone_id]
        except KeyError:
            pass

        # Search for the puppet in the database
        puppet = cast(cls, await super().get_by_phone_id(phone_id))
        if puppet is not None:
            puppet._add_to_cache()
            return puppet

        # Create the puppet if it doesn't exist and if the value of create is True
        if create:
            puppet = cls(phone_id=phone_id, app_business_id=app_business_id)
            await puppet.insert()
            puppet._add_to_cache()
            return puppet

        return None

    @classmethod
    def get_phone_id_from_mxid(cls, mxid: UserID) -> WhatsappPhone | None:
        """
        Get the phone id using the mxid.

        Parameters
        ----------
        mxid : UserID
            The matrix id of the user.
        """
        phone_id = None
        phone_id = cls.mxid_template.parse(mxid)

        if not phone_id:
            return None
        return phone_id

    @classmethod
    async def get_by_mxid(cls, mxid: UserID, *, create: bool = True) -> Optional["Puppet"]:
        """
        Get the mxid of the user.

        Parameters
        ----------
        mxid : UserID
            The matrix id of the user.

        create: bool
            The value to create the puppet if it doesn't exist.
        """
        phone_id = cls.get_phone_id_from_mxid(mxid)
        if phone_id:
            return await cls.get_by_phone_id(phone_id, create=create)
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
        """
        Get all the puppets with custom mxid.
        """
        puppets = await super().all_with_custom_mxid()
        puppet: cls
        for index, puppet in enumerate(puppets):
            try:
                yield cls.by_phone_id[puppet.phone_id]
            except KeyError:
                puppet._add_to_cache()
                yield puppet
