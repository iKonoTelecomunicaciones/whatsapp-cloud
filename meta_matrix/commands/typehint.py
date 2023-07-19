from typing import TYPE_CHECKING

from mautrix.bridge.commands import CommandEvent as BaseCommandEvent

if TYPE_CHECKING:
    from ..__main__ import MetaBridge
    from ..portal import Portal
    from ..user import User


class CommandEvent(BaseCommandEvent):
    bridge: "MetaBridge"
    sender: "User"
    portal: "Portal"
