from typing import Dict, List

from attr import dataclass, ib
from mautrix.types import BaseMessageEventContent, SerializableAttrs


@dataclass
class RowSection(SerializableAttrs):
    """
    Contains the information from the rows of the sections list.

    - id: The id of the row.

    - title: The title of the row.

    - description: The description of the row.
    """

    id: str = ib(metadata={"json": "id"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")
    description: str = ib(metadata={"json": "description"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
        )


@dataclass
class SectionsQuickReply(SerializableAttrs):
    """
    Contains the information from the sections of the interactive message list.

    - title: The title of the section.

    - rows: The information of the selected section.
    """

    title: str = ib(metadata={"json": "title"}, default="")
    rows: List[RowSection] = ib(factory=List, metadata={"json": "rows"})

    @classmethod
    def from_dict(cls, data: dict):
        row_obj = None

        if data.get("rows", []):
            row_obj = [RowSection(**row.__dict__) for row in data.get("rows", [])]

        return cls(
            title=data.get("title", ""),
            rows=row_obj,
        )


@dataclass
class ReplyButton(SerializableAttrs):
    """
    Contains the id and the text of the button

    - id : The id of the button

    - title : The text of the button

    """

    id: str = ib(metadata={"json": "id"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")


@dataclass
class ButtonsQuickReply(SerializableAttrs):
    """
    Contains the type and the obj with the information of the button.

    - reply: The information of the interactive button.

    - type_button: The type of the interactive button.

    """

    reply: ReplyButton = ib(metadata={"json": "reply"}, default={})
    type: str = ib(metadata={"json": "type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            reply=ReplyButton(**data.get("reply", {})),
            type=data.get("type", ""),
        )

@dataclass
class TextReply(SerializableAttrs):
    """
    Contains a text message.

    - text: The text of the obj.

    """

    text: str = ib(metadata={"json": "text"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(text=data.get("text", ""))


@dataclass
class DocumentQuickReply(SerializableAttrs):
    """
    Contains the information of the document header.

    - link: The link of the media.

    - filename: The type of the information.

    """

    link: str = ib(metadata={"json": "link"}, default="")
    filename: str = ib(metadata={"json": "filename"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            link=data.get("link", ""),
            filename=data.get("filename", ""),
        )


@dataclass
class MediaQuickReply(SerializableAttrs):
    """
    Contains the information of the media header.

    - link: The link of the media.
    """

    link: str = ib(metadata={"json": "link"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            link=data.get("link", ""),
        )


@dataclass
class HeaderQuickReply(SerializableAttrs):
    """
    Contains the information of the interactive message.

    - type:  The type of the interactive message.
    - text:  The text of the header, if it is a text header type.
    - image: The image of the header, if it is a image header type.
    - video: The video of the header, if it is a video header type.
    - document: The document of the header, if it is a document header type.
    """

    type: str = ib(metadata={"json": "type"}, default="")
    text: str = ib(metadata={"json": "text"}, default="")
    image: MediaQuickReply = ib(metadata={"json": "image"}, default={})
    video: MediaQuickReply = ib(metadata={"json": "video"}, default={})
    document: DocumentQuickReply = ib(metadata={"json": "document"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            type=data.get("type", ""),
            text=data.get("text", ""),
            video=MediaQuickReply.from_dict(data.get("video", {})),
            document=DocumentQuickReply.from_dict(data.get("document", {})),
            image=MediaQuickReply.from_dict(data.get("image", {})),
        )
@dataclass
class FormResponseMessage(SerializableAttrs, BaseMessageEventContent):
    msgtype: str = ib(default=None, metadata={"json": "msgtype"})
    body: str = ib(default="", metadata={"json": "body"})
    form_data: Dict = ib(factory=Dict, metadata={"json": "form_data"})


@dataclass
class FormMessageContent(SerializableAttrs):
    template_name: str = ib(factory=str, metadata={"json": "template_name"})
    language: str = ib(factory=str, metadata={"json": "language"})
    body_variables: Dict[str, str] = ib(default=None, metadata={"json": "body_variables"})
    header_variables: Dict[str, str] = ib(default=None, metadata={"json": "header_variables"})
    button_variables: Dict[str, str] = ib(default=None, metadata={"json": "button_variables"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            template_name=data.get("template_name", ""),
            language=data.get("language", ""),
            body_variables=data.get("body_variables", {}),
            header_variables=data.get("header_variables", {}),
            button_variables=data.get("button_variables", {}),
        )


@dataclass
class FormMessage(SerializableAttrs):
    msgtype: str = ib(default=None, metadata={"json": "msgtype"})
    body: str = ib(default="", metadata={"json": "body"})
    form_message: FormMessageContent = ib(
        factory=FormMessageContent, metadata={"json": "form_message"}
    )

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            msgtype=data.get("msgtype", ""),
            body=data.get("body", ""),
            form_message=FormMessageContent.from_dict(data.get("form_message", {})),
        )
