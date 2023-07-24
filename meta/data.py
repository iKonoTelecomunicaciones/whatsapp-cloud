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
class MetaPayload(SerializableAttrs):
    url: str = ib(metadata={"json": "url"}, default=None)
    sticker_id: str = ib(metadata={"json": "sticker_id"}, default=None)


@dataclass
class MetaAttachment(SerializableAttrs):
    type: str = ib(metadata={"json": "type"}, default=None)
    payload: MetaPayload = ib(metadata={"json": "payload"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        payload = None
        if data.get("payload"):
            payload = MetaPayload(**data.get("payload", {}))

        return cls(
            type=data.get("type", None),
            payload=payload,
        )


@dataclass
class MetaReplyTo(SerializableAttrs):
    mid: MetaMessageID = ib(metadata={"json": "mid"}, default=None)


@dataclass
class MetaMessageData(SerializableAttrs):
    mid: MetaMessageID = ib(metadata={"json": "mid"})
    text: str = ib(metadata={"json": "text"})
    attachments: MetaAttachment = ib(metadata={"json": "attachments"}, default={})
    reply_to: MetaReplyTo = ib(metadata={"json": "reply_to"}, default=None)

    @classmethod
    def from_dict(cls, data: dict):
        reply_to = None
        if data.get("reply_to"):
            reply_to = MetaReplyTo(**data.get("reply_to", {}))

        try:
            attachments = data.get("attachments", [])[0]
        except IndexError:
            attachments = {}

        return cls(
            mid=data.get("mid"),
            text=data.get("text"),
            attachments=MetaAttachment.from_dict(attachments),
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
class FacebookUserData(SerializableAttrs):
    id: MetaPsID = ib(metadata={"json": "id"})
    first_name: str = ib(metadata={"json": "first_name"})
    last_name: str = ib(metadata={"json": "last_name"})
    profile_pic: str = ib(metadata={"json": "profile_pic"})
    locale: str = ib(metadata={"json": "locale"}, default=None)


@dataclass
class InstagramUserData(SerializableAttrs):
    id: MetaPsID = ib(metadata={"json": "id"})
    name: str = ib(metadata={"json": "name"})
    username: str = ib(metadata={"json": "username"})
    profile_pic: str = ib(metadata={"json": "profile_pic"})
    is_verified_user: bool = ib(metadata={"json": "is_verified_user"})
    follower_count: int = ib(metadata={"json": "follower_count"})
    is_user_follow_business: bool = ib(metadata={"json": "is_user_follow_business"})
    is_business_follow_user: bool = ib(metadata={"json": "is_business_follow_user"})
