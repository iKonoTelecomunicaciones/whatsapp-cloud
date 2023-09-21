from attr import dataclass, ib
from mautrix.types import SerializableAttrs

from .types import WhatsappMessageID, WhatsappPhone, WsBusinessID, WSPhoneID


@dataclass
class WhatsappVideo(SerializableAttrs):
    """
    Contain the video of the customer.

    - id: Te id of the video.

    - hash_url: The hash of the video.

    - caption: The caption of the video.

    - mime_type: The type of the video.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    caption: str = ib(metadata={"json": "caption"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        if data:
            return cls(
                id=data.get("id", ""),
                hash=data.get("sha256", ""),
                caption=data.get("caption", ""),
                mime_type=data.get("mime_type", ""),
            )


@dataclass
class WhatsappImage(SerializableAttrs):
    """
    Contain the image of the customer.

    - id: Te id of the image.

    - hash_url: The hash of the image.

    - caption: The caption of the image.

    - mime_type: The type of the image.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    caption: str = ib(metadata={"json": "caption"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        if data:
            return cls(
                id=data.get("id", ""),
                hash=data.get("sha256", ""),
                caption=data.get("caption", ""),
                mime_type=data.get("mime_type", ""),
            )


@dataclass
class WhatsappText(SerializableAttrs):
    """
    Contain the message of the customer.
    """

    body: str = ib(metadata={"json": "body"}, default="")


@dataclass
class WhatsappMessages(SerializableAttrs):
    """
    Contain the information of the message.

    - from_number: The number of the user, whatsapp api pass this value as "from", so we need to
      change it to "from_number".

    - id: The id of the message

    - timestamp: The time when the message was sent.

    - text: Containt message of the user.

    - type: The type of the message.
    """

    from_number: str = ib(metadata={"json": "from"}, default="")
    id: WhatsappMessageID = ib(metadata={"json": "id"}, default="")
    timestamp: str = ib(metadata={"json": "timestamp"}, default="")
    text: WhatsappText = ib(metadata={"json": "text"}, default={})
    type: str = ib(metadata={"json": "type"}, default="")
    image: WhatsappImage = ib(metadata={"json": "image"}, default={})
    video: WhatsappVideo = ib(metadata={"json": "video"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        text_obj = None
        image_obj = None
        video_obj = None

        if data.get("text"):
            text_obj = WhatsappText(**data.get("text", {}))

        elif data.get("image"):
            image_obj = data.get("image", {})

        elif data.get("video"):
            video_obj = data.get("video", {})

        return cls(
            from_number=data.get("from", ""),
            id=data.get("id", ""),
            timestamp=data.get("timestamp", ""),
            text=text_obj,
            type=data.get("type", ""),
            image=WhatsappImage.from_dict(image_obj),
            video=WhatsappVideo.from_dict(video_obj),
        )


@dataclass
class WhatsappProfile(SerializableAttrs):
    """
    Contain the information of the user.

    - name: The name of the user.
    """

    name: str = ib(metadata={"json": "name"}, default="")


@dataclass
class WhatsappContacts(SerializableAttrs):
    """
    Contain the information of the user.

    - profile: Contain the name of the user.

    - wa_id: The number of the user.
    """

    profile: WhatsappProfile = ib(metadata={"json": "profile"}, default={})
    wa_id: WhatsappPhone = ib(metadata={"json": "wa_id"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        profile_obj = None

        if data.get("profile", {}):
            profile_obj = WhatsappProfile(**data.get("profile", {}))

        return cls(
            profile=profile_obj,
            wa_id=data.get("wa_id", ""),
        )


@dataclass
class WhatsappMetaData(SerializableAttrs):
    """
    Contain the information of the whatsapp business account.

    - display_phone_number: The whatsapp business number.

    - phone_number_id: The id of the whatsapp business number.
    """

    display_phone_number: str = ib(metadata={"json": "display_phone_number"}, default="")
    phone_number_id: WSPhoneID = ib(metadata={"json": "phone_number_id"}, default="")


@dataclass
class WhatsappValue(SerializableAttrs):
    """
    Contain the information of the message, the user and the business account.

    - messaging_product: The type of the message product.

    - metadata: The data of the whatsapp business account.

    - contacts: The information of the user.

    - messages: The data of the message.

    """

    messaging_product: str = ib(metadata={"json": "messaging_product"}, default="")
    metadata: WhatsappMetaData = ib(metadata={"json": "metadata"}, default={})
    contacts: WhatsappContacts = ib(metadata={"json": "contacts"}, default=[])
    messages: WhatsappMessages = ib(metadata={"json": "messages"}, default=[])

    @classmethod
    def from_dict(cls, data: dict):
        metadata_obj = None
        contacts_obj = data.get("contacts", [])[0]
        messages_obj = data.get("messages", [])[0]

        if data.get("metadata"):
            metadata_obj = WhatsappMetaData(**data.get("metadata", {}))

        return cls(
            messaging_product=data.get("messaging_product", ""),
            metadata=metadata_obj,
            contacts=WhatsappContacts.from_dict(contacts_obj),
            messages=WhatsappMessages.from_dict(messages_obj),
        )


@dataclass
class WhatsappChanges(SerializableAttrs):
    """
    Contain relevant information of the message.

    - value: The data of the message.

    - field: The type of the information.
    """

    value: WhatsappValue = ib(metadata={"json": "value"}, default={})
    field: str = ib(metadata={"json": "field"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        value_obj = data.get("value", {})

        return cls(
            value=WhatsappValue.from_dict(value_obj),
            field=data.get("field", ""),
        )


@dataclass
class WhatsappEventEntry(SerializableAttrs):
    """
    Contain relevant information of the request.

    - id: Id of the business account.

    - changes: The data of the message.
    """

    id: WsBusinessID = ib(metadata={"json": "id"})
    changes: WhatsappChanges = ib(metadata={"json": "changes"}, default=[])

    @classmethod
    def from_dict(cls, data: dict):
        changes_obj = data.get("changes", [])[0]

        return cls(
            id=data.get("id", ""),
            changes=WhatsappChanges.from_dict(changes_obj),
        )


@dataclass
class WhatsappMessageEvent(SerializableAttrs):
    """
    Contain the data of the request.

    - object: Contain the information of where arrived the request.

    - entry: The data of the message.
    """

    object: str = ib(metadata={"json": "object"})
    entry: WhatsappEventEntry = ib(metadata={"json": "entry"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        try:
            entry_obj = data.get("entry", [])[0]
        except IndexError:
            entry_obj = {}

        return cls(
            object=data.get("object"),
            entry=WhatsappEventEntry.from_dict(entry_obj),
        )


@dataclass
class WhatsappUserData(SerializableAttrs):
    """
    Contain the data of the user.

    - address: The address of the user.

    - description: The description of the user.

    - email: The email of the user.

    - messaging_product: Where the message arrived.

    - profile_picture_url: The url of the profile picture of the user.
    """

    address: str = ib(metadata={"json": "address"})
    description: str = ib(metadata={"json": "description"})
    email: str = ib(metadata={"json": "email"})
    messaging_product: str = ib(metadata={"json": "messaging_product"})
    profile_picture_url: str = ib(metadata={"json": "profile_picture_url"})


@dataclass
class WhatsappMediaData(SerializableAttrs):
    """
    Contain the data of the media.

    - id: The id of the media.

    - messaging_product: Where the media arrived.

    - url: The url of the media.

    - mime_type: The type of the media.

    - sha256: The hash of the media.

    - file_size: The size of the media.
    """

    id: str = ib(metadata={"json": "id"})
    messaging_product: str = ib(metadata={"json": "messaging_product"})
    url: str = ib(metadata={"json": "url"})
    mime_type: str = ib(metadata={"json": "mime_type"})
    hash: str = ib(metadata={"json": "sha256"})
    file_size: int = ib(metadata={"json": "file_size"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            messaging_product=data.get("messaging_product", ""),
            url=data.get("url", ""),
            mime_type=data.get("mime_type", ""),
            hash=data.get("sha256", ""),
            file_size=data.get("file_size", ""),
        )
