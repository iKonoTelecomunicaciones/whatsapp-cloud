from typing import List

import attr
from attr import dataclass, ib
from mautrix.types import SerializableAttrs

from .types import MetaMessageID, MetaPageID, MetaPsID


@dataclass
class MetaMessageSender(SerializableAttrs):
    id: MetaPsID = ib(metadata={"json": "id"})


@dataclass
class MetaMessageRecipient(SerializableAttrs):
    id: MetaPageID = ib(metadata={"json": "id"})


@dataclass
class MetaReplyTo(SerializableAttrs):
    mid: MetaMessageID = ib(metadata={"json": "mid"}, default=None)


@dataclass
class MetaMessageData(SerializableAttrs):
    mid: MetaMessageID = ib(metadata={"json": "mid"})
    text: str = ib(metadata={"json": "text"})
    attachments: List = ib(metadata={"json": "attachments"})
    reply_to: MetaReplyTo = ib(metadata={"json": "reply_to"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            mid=data.get("mid"),
            text=data.get("text"),
            attachments=data.get("attachments"),
            reply_to=MetaReplyTo(**data.get("reply_to", {})),
        )


@dataclass
class MetaMessaging(SerializableAttrs):
    sender: MetaMessageSender = ib(metadata={"json": "sender"})
    recipient: MetaMessageRecipient = ib(metadata={"json": "recipient"})
    timestamp: str = ib(metadata={"json": "timestamp"})
    message: MetaMessageData = ib(metadata={"json": "message"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            sender=MetaMessageSender(**data.get("sender")),
            recipient=MetaMessageRecipient(**data.get("recipient")),
            timestamp=data.get("timestamp"),
            message=MetaMessageData.from_dict(data.get("message")),
        )


@dataclass
class MetaMessageEntry(SerializableAttrs):
    id: str = ib(metadata={"json": "id"})
    time: str = ib(metadata={"json": "time"})
    messaging: List[MetaMessaging] = ib(metadata={"json": "messaging"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            time=data.get("time"),
            messaging=[
                MetaMessaging.from_dict(messaging) for messaging in data.get("messaging", [])
            ],
        )


@dataclass
class MetaMessageEvent(SerializableAttrs):
    object: str = ib(metadata={"json": "object"})
    entry: List[MetaMessageEntry] = ib(metadata={"json": "entry"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            object=data.get("object"),
            entry=[MetaMessageEntry.from_dict(entry) for entry in data.get("entry", [])],
        )


@dataclass
class MetaUserData(SerializableAttrs):
    id: MetaPsID = ib(metadata={"json": "id"})
    first_name: str = ib(metadata={"json": "first_name"})
    last_name: str = ib(metadata={"json": "last_name"})
    profile_pic: str = ib(metadata={"json": "profile_pic"})
    locale: str = ib(metadata={"json": "locale"}, default=None)


# @dataclass
# class ContentQuickReplay(SerializableAttrs):
#    type: str = attr.ib(default=None, metadata={"json": "type"})
#    header: str = attr.ib(default=None, metadata={"json": "header"})
#    text: str = attr.ib(default=None, metadata={"json": "text"})
#    caption: str = attr.ib(default=None, metadata={"json": "caption"})
#    filename: str = attr.ib(default=None, metadata={"json": "filename"})
#    url: str = attr.ib(default=None, metadata={"json": "url"})
#
#
# @dataclass
# class InteractiveMessageOption(SerializableAttrs):
#    type: str = attr.ib(default=None, metadata={"json": "type"})
#    title: str = attr.ib(default=None, metadata={"json": "title"})
#    description: str = attr.ib(default=None, metadata={"json": "description"})
#    postback_text: str = attr.ib(default=None, metadata={"json": "postbackText"})
#
#
# @dataclass
# class ItemListReplay(SerializableAttrs):
#    title: str = attr.ib(default=None, metadata={"json": "title"})
#    subtitle: str = attr.ib(default=None, metadata={"json": "subtitle"})
#    options: List[InteractiveMessageOption] = attr.ib(metadata={"json": "options"}, factory=list)
#
#
# @dataclass
# class GlobalButtonsListReplay(SerializableAttrs):
#    type: str = attr.ib(default=None, metadata={"json": "type"})
#    title: str = attr.ib(default=None, metadata={"json": "title"})
#
#
# @dataclass
# class InteractiveMessage(SerializableAttrs):
#    type: str = attr.ib(default=None, metadata={"json": "type"})
#    content: ContentQuickReplay = attr.ib(default=None, metadata={"json": "content"})
#    options: List[InteractiveMessageOption] = attr.ib(metadata={"json": "options"}, factory=list)
#    title: str = attr.ib(default=None, metadata={"json": "title"})
#    body: str = attr.ib(default=None, metadata={"json": "body"})
#    msgid: str = attr.ib(default=None, metadata={"json": "msgid"})
#    global_buttons: List[GlobalButtonsListReplay] = attr.ib(
#        metadata={"json": "globalButtons"}, factory=list
#    )
#    items: List[ItemListReplay] = attr.ib(metadata={"json": "items"}, factory=list)
#
#    @property
#    def message(self) -> str:
#        msg = ""
#
#        if self.type == "quick_reply":
#            msg = f"{self.content.header}{self.content.text}"
#
#            for option in self.options:
#                msg = f"{msg}\n{self.options.index(option) + 1}. {option.title}"
#
#        elif self.type == "list":
#            msg = f"{self.title}{self.body}"
#
#            for item in self.items:
#                for option in item.options:
#                    msg = f"{msg}\n{option.postback_text}. {option.title}"
#
#        return msg
#
#
# @dataclass
# class ChatInfo(SerializableAttrs):
#    sender: GupshupMessageSender = None
#    app: GupshupApplication = ""
#
