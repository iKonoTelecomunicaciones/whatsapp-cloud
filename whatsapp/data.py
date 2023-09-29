from attr import dataclass, ib
from mautrix.types import SerializableAttrs

from .types import WhatsappMessageID, WhatsappPhone, WsBusinessID, WSPhoneID


@dataclass
class WhatsappLocation(SerializableAttrs):
    """
    Contain the location of the customer.

    - address: Te address of the location.

    - latitude: The latitude of the location.

    - longitude: The longitude of the location.

    - name: The name of the location .

    - url: The url of the documnet.
    """

    address: str = ib(metadata={"json": "address"}, default="")
    latitude: str = ib(metadata={"json": "latitude"}, default="")
    longitude: str = ib(metadata={"json": "longitude"}, default="")
    name: str = ib(metadata={"json": "name"}, default="")
    url: str = ib(metadata={"json": "url"}, default="")


@dataclass
class WhatsappDocument(SerializableAttrs):
    """
    Contain the documnet of the customer.

    - id: Te id of the documnet.

    - hash: The hash of the documnet.

    - mime_type: The type of the documnet.

    - filename: The name of the documnet.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")
    filename: str = ib(metadata={"json": "filename"}, default=False)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
            filename=data.get("filename", ""),
        )


@dataclass
class WhatsappSticker(SerializableAttrs):
    """
    Contain the sticker of the customer.

    - id: Te id of the sticker.

    - hash: The hash of the sticker.

    - mime_type: The type of the sticker.

    - animated: If the sticker is animated.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")
    animated: bool = ib(metadata={"json": "voice"}, default=False)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
            animated=data.get("animated", False),
        )


@dataclass
class WhatsappAudio(SerializableAttrs):
    """
    Contain the audio of the customer.

    - id: Te id of the audio.

    - hash: The hash of the audio.

    - mime_type: The type of the audio.

    - voice: If the audio is a voice note.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")
    voice: bool = ib(metadata={"json": "voice"}, default=False)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
            voice=data.get("voice", False),
        )


@dataclass
class WhatsappVideo(SerializableAttrs):
    """
    Contain the video of the customer.

    - id: Te id of the video.

    - hash: The hash of the video.

    - mime_type: The type of the video.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
        )


@dataclass
class WhatsappImage(SerializableAttrs):
    """
    Contain the image of the customer.

    - id: Te id of the image.

    - hash: The hash of the image.

    - mime_type: The type of the image.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    hash: str = ib(metadata={"json": "sha256"}, default="")
    mime_type: str = ib(metadata={"json": "mime_type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
        )


@dataclass
class WhatsappText(SerializableAttrs):
    """
    Contain the message of the customer.
    """

    body: str = ib(metadata={"json": "body"}, default="")


@dataclass
class WhatsappErrorData(SerializableAttrs):
    """
    Contain the details of the error.

    - details: A message with the details of the error.
    """

    details: str = ib(metadata={"json": "details"}, default="")


@dataclass
class WhatsappErrors(SerializableAttrs):
    """
    Contain de information of the error.

    - code: The code of the error.

    - title: The title of the error.

    - message: The message of the error.

    - error_data: The data of the error.
    """

    code: str = ib(metadata={"json": "code"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")
    message: str = ib(metadata={"json": "message"}, default="")
    error_data: WhatsappErrorData = ib(metadata={"json": "error_data"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        code_obj = None
        title_obj = None
        message_obj = None
        error_data_obj = None

        if data.get("code"):
            code_obj = data.get("code", "")
        if data.get("title"):
            title_obj = data.get("title", "")
        if data.get("message"):
            message_obj = data.get("message", "")
        if data.get("error_data"):
            error_data_obj = WhatsappErrorData(**data.get("error_data", {}))

        return cls(
            code=code_obj,
            title=title_obj,
            message=message_obj,
            error_data=error_data_obj,
        )


@dataclass
class WhatsappStatusesEvent(SerializableAttrs):
    """
    Contain the information of the error status.

    - id: The id of the message error.

    - status: The status of the message error.

    - timestamp: The time when the message error was sent.

    - recipient_id: The number of the user.

    - errors: The information of the error.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    status: str = ib(metadata={"json": "status"}, default="")
    timestamp: str = ib(metadata={"json": "timestamp"}, default="")
    recipient_id: str = ib(metadata={"json": "recipient_id"}, default="")
    errors: WhatsappErrors = ib(metadata={"json": "errors"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        error_obj = None

        try:
            error_obj = data.get("errors", [])[0]
        except IndexError:
            error_obj = {}

        return cls(
            id=data.get("id", ""),
            status=data.get("status", ""),
            timestamp=data.get("timestamp", ""),
            recipient_id=data.get("recipient_id", ""),
            errors=WhatsappErrors.from_dict(error_obj),
        )


@dataclass
class WhatsappContext(SerializableAttrs):
    """
    Contains the information from the reply message.

    - from_number: The number of the user, whatsapp api pass this value as "from", so we need to
      change it to "from_number".

    - id: The id of the message to which the user is replying.
    """

    from_number: str = ib(metadata={"json": "from"}, default="")
    id: WhatsappMessageID = ib(metadata={"json": "id"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            from_number=data.get("from", ""),
            id=data.get("id", ""),
        )


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
    context: WhatsappContext = ib(metadata={"json": "context"}, default={})
    text: WhatsappText = ib(metadata={"json": "text"}, default={})
    type: str = ib(metadata={"json": "type"}, default="")
    image: WhatsappImage = ib(metadata={"json": "image"}, default={})
    video: WhatsappVideo = ib(metadata={"json": "video"}, default={})
    audio: WhatsappAudio = ib(metadata={"json": "audio"}, default={})
    sticker: WhatsappSticker = ib(metadata={"json": "sticker"}, default={})
    document: WhatsappDocument = ib(metadata={"json": "document"}, default={})
    location: WhatsappLocation = ib(metadata={"json": "location"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        context_obj = None
        text_obj = None
        image_obj = None
        video_obj = None
        audio_obj = None
        sticker_obj = None
        document_obj = None

        if data.get("context", {}):
            context_obj = WhatsappContext.from_dict(data.get("context", {}))

        if data.get("text", ""):
            text_obj = WhatsappText(**data.get("text", {}))

        elif data.get("image", ""):
            image_obj = WhatsappImage.from_dict(data.get("image", {}))

        elif data.get("video", ""):
            video_obj = WhatsappVideo.from_dict(data.get("video", {}))

        elif data.get("audio", ""):
            audio_obj = WhatsappAudio.from_dict(data.get("audio", {}))

        elif data.get("sticker", ""):
            sticker_obj = WhatsappSticker.from_dict(data.get("sticker", {}))

        elif data.get("document", ""):
            document_obj = WhatsappDocument.from_dict(data.get("document", {}))

        return cls(
            from_number=data.get("from", ""),
            id=data.get("id", ""),
            timestamp=data.get("timestamp", ""),
            context=context_obj,
            text=text_obj,
            type=data.get("type", ""),
            image=image_obj,
            video=video_obj,
            audio=audio_obj,
            sticker=sticker_obj,
            document=document_obj,
            location=WhatsappLocation(**data.get("location", {})),
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
    contacts: WhatsappContacts = ib(metadata={"json": "contacts"}, default={})
    messages: WhatsappMessages = ib(metadata={"json": "messages"}, default={})
    statuses: WhatsappStatusesEvent = ib(metadata={"json": "statuses"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        metadata_obj = None
        contacts_obj = None
        messages_obj = None
        statuses_obj = None

        if data.get("metadata"):
            metadata_obj = WhatsappMetaData(**data.get("metadata", {}))

        try:
            contacts_obj = data.get("contacts", [])[0]
        except IndexError:
            contacts_obj = {}

        try:
            messages_obj = data.get("messages", [])[0]
        except IndexError:
            messages_obj = {}

        try:
            statuses_obj = data.get("statuses", [])[0]
        except IndexError:
            statuses_obj = {}

        return cls(
            messaging_product=data.get("messaging_product", ""),
            metadata=metadata_obj,
            contacts=WhatsappContacts.from_dict(contacts_obj),
            messages=WhatsappMessages.from_dict(messages_obj),
            statuses=WhatsappStatusesEvent.from_dict(statuses_obj),
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
    changes: WhatsappChanges = ib(metadata={"json": "changes"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        try:
            changes_obj = data.get("changes", [])[0]
        except IndexError:
            changes_obj = {}

        return cls(
            id=data.get("id", ""),
            changes=WhatsappChanges.from_dict(changes_obj),
        )


@dataclass
class WhatsappEvent(SerializableAttrs):
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
