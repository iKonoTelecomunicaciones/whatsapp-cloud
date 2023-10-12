from typing import List

from attr import dataclass, ib
from mautrix.types import SerializableAttrs


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
class ActionQuickReply(SerializableAttrs):
    """
    Contains the buttons of the interactive message.

    - name: The name of the location message.

    -  button: The name of the button in a list message.

    - buttons: The information of the buttons in a quick reply message.

    - sections: The information of the sections in a list message.
    """

    name: str = ib(metadata={"json": "name"}, default="")
    button: str = ib(metadata={"json": "button"}, default="")
    buttons: List[ButtonsQuickReply] = ib(factory=List, metadata={"json": "buttons"})
    sections: List[SectionsQuickReply] = ib(factory=List, metadata={"json": "sections"})

    @classmethod
    def from_dict(cls, data: dict):
        button_obj = None
        section_obj = None

        if data.get("buttons", []):
            button_obj = [
                ButtonsQuickReply(**button.__dict__) for button in data.get("buttons", [])
            ]

        if data.get("sections", []):
            section_obj = [
                SectionsQuickReply(**section.__dict__) for section in data.get("sections", [])
            ]

        return cls(
            name=data.get("name", ""),
            button=data.get("button", ""),
            buttons=button_obj,
            sections=section_obj,
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
class InteractiveMessage(SerializableAttrs):
    """
    Contains the information from the interactive buttons message.

    - type: The type of the interactive message.

    - header: The information of the interactive header message.

    - body: The information of the interactive body message.

    - footer: The information of the interactive footer message.

    - action: The information of the interactive buttons message.

    """

    type: str = ib(metadata={"json": "type"}, default="")
    header: HeaderQuickReply = ib(metadata={"json": "header"}, default={})
    body: TextReply = ib(metadata={"json": "body"}, default={})
    footer: TextReply = ib(metadata={"json": "footer"}, default={})
    action: ActionQuickReply = ib(metadata={"json": "action"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        action_obj = None
        body_obj = None
        footer_obj = None

        if data.get("header", {}):
            header_obj = HeaderQuickReply.from_dict(data.get("header", {}))

        if data.get("action", []):
            action_obj = ActionQuickReply.from_dict(data.get("action", {}))

        if data.get("body", {}):
            body_obj = TextReply.from_dict(data.get("body", {}))

        if data.get("footer", {}):
            footer_obj = TextReply.from_dict(data.get("footer", {}))

        return cls(
            type=data.get("type", ""),
            header=header_obj,
            body=body_obj,
            footer=footer_obj,
            action=action_obj,
        )

    @property
    def button_message(self) -> str:
        """
        Obtain a message text with the information of the interactive quick reply message.
        """
        msg = f"""
            {self.header.text if self.header else ''}\n
            {self.body.text  if self.body else ''}\n
            {self.footer.text  if self.footer else ''}
        """
        for button in self.action.buttons:
            msg = f"{msg}\n{button.reply.id}. {button.reply.title}"

        return msg

    @property
    def list_message(self) -> str:
        """
        Obtain a message text with the information of the interactive list message.
        """
        msg = f"""
            {self.header.text if self.header else ''}\n
            {self.body.text  if self.body else ''}\n
            {self.footer.text  if self.footer else ''}
        """
        for section in self.action.sections:
            for row in section.rows:
                msg = f"{msg}\n{section.title}.\n {row.id}. {row.title}\n   {row.description}"

        return msg


@dataclass
class EventInteractiveMessage(SerializableAttrs):
    """
    Contains the information of the interactive message.

    - body: The message of the interactive message.

    - interactive_message: The data of the interactive message.

    - msgtype: The type of the interactive message.
    """

    body: str = ib(metadata={"json": "body"}, default="")
    interactive_message: InteractiveMessage = ib(
        metadata={"json": "interactive_message"}, default={}
    )
    msgtype: str = ib(metadata={"json": "msgtype"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        interactive_message_obj = None

        if data.get("interactive_message", {}):
            interactive_message_obj = InteractiveMessage.from_dict(
                data.get("interactive_message", {})
            )

        return cls(
            body=data.get("body", ""),
            interactive_message=interactive_message_obj,
            msgtype=data.get("msgtype", ""),
        )
