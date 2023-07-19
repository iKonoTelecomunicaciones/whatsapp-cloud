from typing import List

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
    reply_to: MetaReplyTo = ib(metadata={"json": "reply_to"}, default=None)

    @classmethod
    def from_dict(cls, data: dict):
        reply_to = None
        if data.get("reply_to"):
            reply_to = MetaReplyTo(**data.get("reply_to", {}))

        return cls(
            mid=data.get("mid"),
            text=data.get("text"),
            attachments=data.get("attachments"),
            reply_to=reply_to,
        )


@dataclass
class MetaDeliveryData(SerializableAttrs):
    mids: List[MetaMessageID] = ib(metadata={"json": "mids"})
    watermark: int = ib(metadata={"json": "watermark"})


@dataclass
class MetaReadData(SerializableAttrs):
    watermark: int = ib(metadata={"json": "watermark"})


@dataclass
class MetaMessaging(SerializableAttrs):
    sender: MetaMessageSender = ib(metadata={"json": "sender"})
    recipient: MetaMessageRecipient = ib(metadata={"json": "recipient"})
    timestamp: str = ib(metadata={"json": "timestamp"})
    message: MetaMessageData = ib(metadata={"json": "message"}, default={})
    delivery: MetaDeliveryData = ib(metadata={"json": "delivery"}, default={})
    read: MetaReadData = ib(metadata={"json": "read"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        message = None
        delivery = None
        read = None

        if data.get("message"):
            message = MetaMessageData.from_dict(data.get("message", {}))
        elif data.get("delivery"):
            delivery = MetaDeliveryData(**data.get("delivery", {}))
        elif data.get("read"):
            read = MetaReadData(**data.get("read", {}))

        return cls(
            sender=MetaMessageSender(**data.get("sender")),
            recipient=MetaMessageRecipient(**data.get("recipient")),
            timestamp=data.get("timestamp"),
            message=message,
            delivery=delivery,
            read=read,
        )


@dataclass
class MetaEventEntry(SerializableAttrs):
    id: str = ib(metadata={"json": "id"})
    time: str = ib(metadata={"json": "time"})
    messaging: MetaMessaging = ib(metadata={"json": "messaging"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        try:
            messaging_obj = data.get("messaging", [])[0]
        except IndexError:
            messaging_obj = {}

        return cls(
            id=data.get("id"),
            time=data.get("time"),
            messaging=MetaMessaging.from_dict(messaging_obj),
        )


@dataclass
class MetaMessageEvent(SerializableAttrs):
    object: str = ib(metadata={"json": "object"})
    entry: MetaEventEntry = ib(metadata={"json": "entry"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        try:
            entry_obj = data.get("entry", [])[0]
        except IndexError:
            entry_obj = {}

        return cls(
            object=data.get("object"),
            entry=MetaEventEntry.from_dict(entry_obj),
        )


@dataclass
class MetaStatusEvent(SerializableAttrs):
    object: str = ib(metadata={"json": "object"})
    entry: MetaEventEntry = ib(metadata={"json": "entry"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        try:
            entry_obj = data.get("entry", [])[0]
        except IndexError:
            entry_obj = {}

        return cls(
            object=data.get("object"),
            entry=MetaEventEntry.from_dict(entry_obj),
        )


@dataclass
class MetaUserData(SerializableAttrs):
    id: MetaPsID = ib(metadata={"json": "id"})
    first_name: str = ib(metadata={"json": "first_name"})
    last_name: str = ib(metadata={"json": "last_name"})
    profile_pic: str = ib(metadata={"json": "profile_pic"})
    locale: str = ib(metadata={"json": "locale"}, default=None)
