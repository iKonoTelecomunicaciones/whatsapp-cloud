from mautrix.util.async_db import Database

from .message import Message
from .meta_application import MetaApplication
from .portal import Portal
from .puppet import Puppet
from .upgrade import upgrade_table
from .user import User


def init(db: Database) -> None:
    for table in (Puppet, Portal, User, Message, MetaApplication):
        table.db = db


__all__ = ["upgrade_table", "Puppet", "Portal", "Message", "MetaApplication", "init"]
