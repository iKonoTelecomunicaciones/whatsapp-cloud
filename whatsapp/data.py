import json

from attr import dataclass, ib
from mautrix.types import BaseMessageEventContent, SerializableAttrs

from .types import WhatsappMessageID, WhatsappPhone, WsBusinessID, WSPhoneID


@dataclass
class TemplateMessage(SerializableAttrs, BaseMessageEventContent):
    msgtype: str = ib(default=None, metadata={"json": "msgtype"})
    body: str = ib(default="", metadata={"json": "body"})
    template_message: list = ib(factory=list, metadata={"json": "template_message"})


@dataclass
class ListReply(SerializableAttrs):
    """
    Contains the information from the rows of the sections list.

    - id: The id of the option in the row.

    - title: The title of the option in the row.

    - description: The description of the option in the row.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")
    description: str = ib(metadata={"json": "description"}, default="")


@dataclass
class ButtonReply(SerializableAttrs):
    """
    Contains the id and the text of the button

    - id: The id of the button

    - title: The text of the button

    """

    id: str = ib(metadata={"json": "id"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")


@dataclass
class NFMReply(SerializableAttrs):
    """
    Contains the information of the NFM reply.

    - response_json: The json of the response.
    - body: The body of the response.
    - name: The name of the response.
    """

    response_json: dict = ib(metadata={"json": "response_json"}, default="")
    body: str = ib(metadata={"json": "body"}, default="")
    name: str = ib(metadata={"json": "name"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            response_json=json.loads(data.get("response_json", "{}")),
            body=data.get("body", ""),
            name=data.get("name", ""),
        )


@dataclass
class ButtonMessage(SerializableAttrs):
    """
    Contains the information of the button message.

    - payload: The value of the button.

    - text: The text of the button.
    """

    payload: str = ib(metadata={"json": "payload"}, default="")
    text: str = ib(metadata={"json": "text"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            payload=data.get("payload", ""),
            text=data.get("text", ""),
        )


@dataclass
class InteractiveMessage(SerializableAttrs):
    """
    Contains the response from the user who interacted with the interactive message.

    - type: The type of the interactive message.

    - button_reply: The infomation of the button.
    """

    type: str = ib(metadata={"json": "type"}, default="")
    button_reply: ButtonReply = ib(metadata={"json": "button_reply"}, default={})
    list_reply: ListReply = ib(metadata={"json": "list_reply"}, default={})
    nfm_reply: NFMReply = ib(metadata={"json": "nfm_reply"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            type=data.get("type", ""),
            button_reply=ButtonReply(**data.get("button_reply", {})),
            list_reply=ListReply(**data.get("list_reply", {})),
            nfm_reply=NFMReply.from_dict(data.get("nfm_reply", {})),
        )

    @property
    def list_reply_message(self) -> str:
        title = self.list_reply.title if self.list_reply else ""
        msg = f"{title}"

        return msg


@dataclass
class WhatsappReaction(SerializableAttrs):
    """
    Contain the information of the reaction.

    - message_id: The id of the message.

    - emoji: The emoji of the reaction.
    """

    message_id: str = ib(metadata={"json": "message_id"}, default="")
    emoji: str = ib(metadata={"json": "emoji"}, default="")


@dataclass
class WhatsappMedia(SerializableAttrs):
    """
    Contain the image of the customer.

    - id: The id of the image.

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
class WhatsappLocation(SerializableAttrs):
    """
    Contain the location of the customer.

    - address: The address of the location.

    - latitude: The latitude of the location.

    - longitude: The longitude of the location.

    - name: The name of the location .

    - url: The url of the document.
    """

    address: str = ib(metadata={"json": "address"}, default="")
    latitude: str = ib(metadata={"json": "latitude"}, default="")
    longitude: str = ib(metadata={"json": "longitude"}, default="")
    name: str = ib(metadata={"json": "name"}, default="")
    url: str = ib(metadata={"json": "url"}, default="")


@dataclass
class WhatsappDocument(WhatsappMedia):
    """
    Contain the document of the customer.

    - id: The id of the document.

    - hash: The hash of the document.

    - mime_type: The type of the document.

    - filename: The name of the document.
    """

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
class WhatsappSticker(WhatsappMedia):
    """
    Contain the sticker of the customer.

    - id: The id of the sticker.

    - hash: The hash of the sticker.

    - mime_type: The type of the sticker.

    - animated: If the sticker is animated.
    """

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
class WhatsappAudio(WhatsappMedia):
    """
    Contain the audio of the customer.

    - id: The id of the audio.

    - hash: The hash of the audio.

    - mime_type: The type of the audio.

    - voice: If the audio is a voice note.
    """

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
class WhatsappVideo(WhatsappMedia):
    """
    Contain the video of the customer.

    - id: The id of the video.

    - hash: The hash of the video.

    - mime_type: The type of the video.
    """

    caption: str | None = ib(metadata={"json": "caption"}, default=None)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
            caption=data.get("caption", None),
        )


@dataclass
class WhatsappImage(WhatsappMedia):
    """
    Contain the image of the customer.

    - id: The id of the image.

    - hash: The hash of the image.

    - mime_type: The type of the image.
    """

    caption: str | None = ib(metadata={"json": "caption"}, default=None)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            hash=data.get("sha256", ""),
            mime_type=data.get("mime_type", ""),
            caption=data.get("caption", None),
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
    error_data: WhatsappErrorData = ib(metadata={"json": "error_data"}, default={})

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

    - image: Image object that contains the information of the image that the user sent.

    - video: Video object that contains the information of the video that the user sent.

    - audio: Audio object that contains the information of the audio that the user sent.

    - sticker: Sticker object that contains the information of the sticker that the user sent.

    - document: Document object that contains the information of the document that the user sent.

    - location: Location object that contains the information of the location that the user sent.

    - reaction: Reaction object that contains the information of the reaction that the user sent.

    - interactive: Interactive object that contains the information of the interactive message that the user sent.

    - button: Button object that contains the information of the button message that the user sent.
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
    reaction: WhatsappReaction = ib(metadata={"json": "reaction"}, default={})
    interactive: InteractiveMessage = ib(metadata={"json": "interactive"}, default={})
    button: ButtonMessage = ib(metadata={"json": "button"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        context_obj = None
        text_obj = None
        image_obj = None
        video_obj = None
        audio_obj = None
        sticker_obj = None
        document_obj = None
        interactive_obj = None
        button_obj = None

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

        elif data.get("interactive", ""):
            interactive_obj = InteractiveMessage.from_dict(data.get("interactive", {}))

        elif data.get("button", ""):
            button_obj = ButtonMessage.from_dict(data.get("button", {}))

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
            reaction=WhatsappReaction(**data.get("reaction", {})),
            interactive=interactive_obj,
            button=button_obj,
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
