from asyncio import AbstractEventLoop, get_event_loop
from logging import Logger, getLogger

from aiohttp import ClientSession
from mautrix.appservice import AppServiceAPI, IntentAPI
from mautrix.client import StateStore
from yarl import URL

from whatsapp_matrix.config import Config


class Ghost:
    loop: AbstractEventLoop
    log: Logger = getLogger("whatsapp.ghost")

    def __init__(
        self,
        mxid: str,
        config: Config,
        state_store: StateStore,
        client_session: ClientSession,
        loop: AbstractEventLoop = None,
    ) -> None:
        self.config = config
        self.loop = loop or get_event_loop()
        self.mxid = mxid
        self.api = AppServiceAPI(
            base_url=URL(self.config["homeserver.address"]),
            bot_mxid=mxid,
            token=self.config["appservice.as_token"],
            identity=mxid,
            state_store=state_store,
            client_session=client_session,
            log=self.log,
            loop=self.loop,
            bridge_name=self.config["appservice.ghost_displayname"],
        )
        self.intent = IntentAPI(self.mxid, self.api, state_store=self.api.state_store)

    @classmethod
    def get_mxid(cls, name: str, domain: str) -> str:
        return f"@{name}:{domain}"

    async def create(self) -> None:
        await self.intent.ensure_registered()
        await self.intent.set_presence(status="available")
        displayname = self.config["appservice.ghost_displayname"]
        if displayname:
            try:
                await self.intent.set_displayname(displayname)
            except Exception:
                self.log.exception("Failed to set bot displayname")

    async def invite(self, room_id: str, reason: str = None) -> None:
        await self.intent.invite_user(room_id, self.mxid, reason=reason)
