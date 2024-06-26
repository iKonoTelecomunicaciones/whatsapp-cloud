from mautrix.util.async_db import Database

from .message import Message
from .portal import Portal
from .puppet import Puppet
from .reaction import Reaction
from .upgrade import upgrade_table
from .user import User
from .whatsapp_application import WhatsappApplication


def init(db: Database) -> None:
    for table in (Puppet, Portal, User, Message, WhatsappApplication, Reaction):
        table.db = db


__all__ = [
    "upgrade_table",
    "Puppet",
    "Portal",
    "Message",
    "WhatsappApplication",
    "Reaction",
    "init",
]
