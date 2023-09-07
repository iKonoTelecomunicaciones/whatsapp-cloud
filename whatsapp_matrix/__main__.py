from mautrix.bridge import Bridge
from mautrix.types import RoomID, UserID

from whatsapp import WhatsappClient, WhatsappHandler

from . import commands
from .config import Config
from .db import init as init_db
from .db import upgrade_table
from .matrix import MatrixHandler
from .portal import Portal
from .puppet import Puppet
from .user import User
from .version import linkified_version, version
from .web import ProvisioningAPI


class WhatsappBridge(Bridge):
    name = "whatsapp-cloud"
    module = "whatsapp_matrix"
    command = "python -m whatsapp-cloud"
    description = "A Matrix-Whatsapp relaybot bridge."
    repo_url = "https://github.com/iKonoTelecomunicaciones/whatsapp-cloud"
    version = version
    markdown_version = linkified_version
    config_class = Config
    matrix_class = MatrixHandler
    upgrade_table = upgrade_table

    config: Config
    meta: WhatsappHandler
    whatsapp_client: WhatsappClient

    provisioning_api: ProvisioningAPI

    def preinit(self) -> None:
        super().preinit()

    def prepare_db(self) -> None:
        super().prepare_db()
        init_db(self.db)

    def prepare_bridge(self) -> None:
        self.meta = WhatsappHandler(loop=self.loop, config=self.config)
        super().prepare_bridge()
        self.whatsapp_client = WhatsappClient(config=self.config, loop=self.loop)
        self.az.app.add_subapp(self.config["whatsapp.webhook_path"], self.meta.app)
        cfg = self.config["bridge.provisioning"]
        self.provisioning_api = ProvisioningAPI(
            shared_secret=cfg["shared_secret"],
        )
        self.az.app.add_subapp(cfg["prefix"], self.provisioning_api.app)

    async def start(self) -> None:
        User.init_cls(self)
        self.add_startup_actions(Puppet.init_cls(self))
        Portal.init_cls(self)
        await super().start()

    def prepare_stop(self) -> None:
        self.log.debug("Stopping puppet syncers")
        for puppet in Puppet.by_custom_mxid.values():
            puppet.stop()

    async def get_user(self, user_id: UserID, create: bool = True) -> User:
        return await User.get_by_mxid(user_id, create=create)

    async def get_portal(self, room_id: RoomID) -> Portal:
        return await Portal.get_by_mxid(room_id)

    async def get_puppet(self, user_id: UserID, create: bool = False) -> Puppet:
        return await Puppet.get_by_mxid(user_id, create=create)

    async def get_double_puppet(self, user_id: UserID) -> Puppet:
        return await Puppet.get_by_custom_mxid(user_id)

    def is_bridge_ghost(self, user_id: UserID) -> bool:
        return bool(Puppet.get_id_from_mxid(user_id))

    async def count_logged_in_users(self) -> int:
        return len([user for user in User.by_business_id.values() if user.app_business_id])


WhatsappBridge().run()
