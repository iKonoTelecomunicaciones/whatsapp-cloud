from __future__ import annotations

import re
from collections.abc import AsyncGenerator, AsyncIterable, Awaitable
from typing import TYPE_CHECKING, cast

from mautrix.appservice import IntentAPI
from mautrix.bridge import BasePuppet, async_getter_lock
from mautrix.types import UserID
from mautrix.util.simple_template import SimpleTemplate

from whatsapp.types import WhatsappBSUID, WhatsappPhone, WhatsappUsername

from .config import Config
from .db import Puppet as DBPuppet

if TYPE_CHECKING:
    from .__main__ import WhatsappBridge


class Puppet(DBPuppet, BasePuppet):
    by_identifier_id: dict[WhatsappPhone | WhatsappBSUID, "Puppet"] = {}
    by_custom_mxid: dict[UserID, Puppet] = {}
    hs_domain: str
    mxid_template: SimpleTemplate[str]

    config: Config

    default_mxid_intent: IntentAPI
    default_mxid: UserID

    def __init__(
        self,
        phone_id: WhatsappPhone,
        bsuid: WhatsappBSUID | None = None,
        display_name: str | None = None,
        is_registered: bool = False,
        custom_mxid: UserID | None = None,
        username: WhatsappUsername | None = None,
        access_token: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(
            phone_id=phone_id,
            display_name=display_name,
            custom_mxid=custom_mxid,
            username=username,
            id=id,
        )

        if not phone_id and not bsuid:
            bsuid = self.mxid_template.parse(self.custom_mxid)

        self.bsuid = bsuid
        identifier = self.phone_id if self.phone_id else self.bsuid
        self.log = self.log.getChild(identifier)

        self.access_token = access_token
        self.is_registered = is_registered
        self.default_mxid = self.get_mxid_from_identifier(identifier)
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

    def _add_to_cache(self) -> None:
        if self.phone_id:
            self.by_identifier_id[self.phone_id] = self
        if self.bsuid:
            self.by_identifier_id[self.bsuid] = self
        if self.custom_mxid:
            self.by_custom_mxid[self.custom_mxid] = self

    @property
    def mxid(self) -> UserID:
        return UserID(
            self.mxid_template.format_full(self.phone_id if self.phone_id else self.bsuid)
        )

    async def save(self) -> None:
        await self.update()

    async def update_info(self, info: dict) -> None:
        update = False
        update = await self._update_name(info) or update

        if self.username != info.get("profile", {}).get("username"):
            self.username = info.get("profile", {}).get("username")
            update = True

        if update:
            await self.update()

    @classmethod
    def _get_displayname(cls, info: dict) -> str:
        """
        Get the name of the user to use on the matrix room.

        Parameters
        ----------
        info : Dict
            The name of the user and his phone id.
        """
        identifier = info.wa_id if info.wa_id else info.user_id
        display_name = info.profile.name if info.profile else f"user_{identifier}"
        variables = {"displayname": display_name, "userid": identifier}
        puppet_displayname: str = cls.config["bridge.whatsapp_cloud.displayname_template"]

        return puppet_displayname.format(**variables)

    async def _update_name(self, info: dict) -> bool:
        """
        Update the name of the user.

        Parameters
        ----------
        info : Dict
            The name of the user and his phone id.
        """
        # If the puppet already exists, validate if the name is the same as the one in the database,
        # like user_name (WB), because the _get_displayname function will return user_name (WB) (WB)
        # and the display_name will be updated.
        if not info.get("profile"):
            return False

        if info.profile.name == self.display_name:
            return False
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
    def get_mxid_from_identifier(cls, identifier: WhatsappPhone | WhatsappUsername) -> UserID:
        return UserID(cls.mxid_template.format_full(identifier))

    async def get_displayname(self) -> str:
        return await self.intent.get_displayname(self.mxid)

    @classmethod
    @async_getter_lock
    async def get_by_identifier(
        cls,
        phone_id: WhatsappPhone | None = None,
        bsuid: WhatsappUsername | None = None,
        *,
        create: bool = True,
    ) -> "Puppet" | None:
        """
        Get the puppet using the identifier.

        Parameters
        ----------
        phone_id : WhatsappPhone | None
            The phone id of the user.
        bsuid : WhatsappUsername | None
            The bsuid of the user.
        create : bool
            The value to create the puppet if it doesn't exist.
        """
        if phone_id is None and bsuid is None:
            raise ValueError("Either phone_id or bsuid must be provided")

        if phone_id in cls.by_identifier_id:
            return cls.by_identifier_id[phone_id]

        if bsuid in cls.by_identifier_id:
            return cls.by_identifier_id[bsuid]

        mxid = None
        puppet = None
        if phone_id:
            mxid = cls.get_mxid_from_identifier(phone_id)

            # Search for the puppet in the database
            puppet = cast(cls, await super().get_by_identifier(mxid))

        if bsuid and puppet is None:
            mxid = cls.get_mxid_from_identifier(bsuid)
            puppet = cast(cls, await super().get_by_identifier(mxid))

        if puppet is not None:
            if phone_id and not puppet.phone_id:
                puppet.phone_id = phone_id
                await puppet.update()
            if bsuid and not puppet.bsuid:
                puppet.bsuid = bsuid
                await puppet.update()

            puppet._add_to_cache()
            return puppet

        # Create the puppet if it doesn't exist and if the value of create is True
        if create:
            puppet = cls(phone_id=phone_id, bsuid=bsuid)
            await puppet.insert()
            puppet._add_to_cache()
            return puppet

        return None

    @classmethod
    async def get_by_id(cls, id: int) -> "Puppet" | None:
        """
        Get the puppet using the id.

        Parameters
        ----------
        id : int
            The id of the puppet.
        """
        puppet = cast(cls, await super().get_by_id(id))
        if puppet:
            puppet._add_to_cache()
            return puppet
        return None

    @classmethod
    async def get_by_mxid(cls, mxid: UserID, *, create: bool = True) -> "Puppet" | None:
        """
        Get the mxid of the user.

        Parameters
        ----------
        mxid : UserID
            The matrix id of the user.

        create: bool
            The value to create the puppet if it doesn't exist.
        """
        identifier = cls.mxid_template.parse(mxid)

        if not identifier:
            return None

        # A BSUID has the form <COUNTRY_CODE>.<ID> (e.g. COL.1234);
        # a phone number consists only of digits (e.g. 573141234567).
        is_bsuid = bool(re.match(r"^[A-Za-z]+\.\S+$", identifier))
        if is_bsuid:
            return await cls.get_by_identifier(bsuid=identifier, create=create)

        return await cls.get_by_identifier(phone_id=identifier, create=create)

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
                yield cls.by_custom_mxid[puppet.custom_mxid]
            except KeyError:
                puppet._add_to_cache()
                yield puppet
