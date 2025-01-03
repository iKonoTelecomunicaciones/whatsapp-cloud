from attr import dataclass, ib
from mautrix.types import SerializableAttrs, BaseMessageEventContent
from typing import Dict


@dataclass
class FormMessage(SerializableAttrs, BaseMessageEventContent):
    msgtype: str = ib(default=None, metadata={"json": "msgtype"})
    body: str = ib(default="", metadata={"json": "body"})
    form_data: Dict = ib(factory=Dict, metadata={"json": "form_data"})
