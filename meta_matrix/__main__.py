from mautrix.bridge import Bridge
from mautrix.types import RoomID, UserID

from meta import MetaClient, MetaHandler

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


class MetaBridge(Bridge):
    name = "meta-matrix"
    module = "meta_matrix"
    command = "python -m meta-matrix"
    description = "A Matrix-Meta relaybot bridge."
    repo_url = "https://github.com/iKonoTelecomunicaciones/meta-matrix"
    version = version
    markdown_version = linkified_version
    config_class = Config
    matrix_class = MatrixHandler
    upgrade_table = upgrade_table

    config: Config
    meta: MetaHandler
    meta_client: MetaClient

    provisioning_api: ProvisioningAPI

    def preinit(self) -> None:
        super().preinit()

    def prepare_db(self) -> None:
        super().prepare_db()
        init_db(self.db)

    def prepare_bridge(self) -> None:
        self.meta = MetaHandler(loop=self.loop, config=self.config)
        super().prepare_bridge()
        self.meta_client = MetaClient(config=self.config, loop=self.loop)
        self.az.app.add_subapp(self.config["meta.webhook_path"], self.meta.app)
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
        return len([user for user in User.by_page_id.values() if user.app_page_id])


MetaBridge().run()
