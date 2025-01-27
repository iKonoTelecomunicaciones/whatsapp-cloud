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

    def button_message(self, button_item_format: str) -> str:
        """
        Obtain a message text with the information of the interactive quick reply message.
        """
        msg = f"""{self.header.text if self.header else ''}
            {self.body.text  if self.body else ''}
            {self.footer.text  if self.footer else ''}
        """
        message: str = button_item_format or ""
        for index, button in enumerate(self.action.buttons, start=1):
            msg += message.format(index=index, title=button.reply.title, id=button.reply.id)
        return msg

    def list_message(self, list_item_format: str) -> str:
        """
        Obtain a message text with the information of the interactive list message.
        """
        msg = f"""{self.header.text if self.header else ''}
            {self.body.text  if self.body else ''}
            {self.footer.text  if self.footer else ''}
        """
        message: str = list_item_format or ""
        for section_index, section in enumerate(self.action.sections, start=1):
            for row_index, row in enumerate(section.rows, start=1):
                msg += message.format(
                    section_title=section.title,
                    section_index=section_index,
                    row_title=row.title,
                    row_description=row.description,
                    row_id=row.id,
                    row_index=row_index,
                )
        return msg

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
