from typing import Dict

from attr import dataclass, ib
from mautrix.types import BaseMessageEventContent, SerializableAttrs


@dataclass
class FormMessage(SerializableAttrs, BaseMessageEventContent):
    msgtype: str = ib(default=None, metadata={"json": "msgtype"})
    body: str = ib(default="", metadata={"json": "body"})
    form_data: Dict = ib(factory=Dict, metadata={"json": "form_data"})
