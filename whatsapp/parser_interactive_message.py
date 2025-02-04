from typing import List

from attr import dataclass, ib
from mautrix.types import SerializableAttrs

from whatsapp.interactive_message import (
    ActionQuickReply,
    ButtonsQuickReply,
    DocumentQuickReply,
    HeaderQuickReply,
    InteractiveMessage,
    MediaQuickReply,
    RowSection,
    SectionsQuickReply,
    TextReply,
)


@dataclass
class OptionsInteractiveMessage(InteractiveMessage):
    """
    Contains the information of the options of a section.

    - description: The description of the option.
    - postback_text: The identifier of the option.
    - title: The title of the option.
    - type: The type of the option.
    """

    description: str = ib(metadata={"json": "description"}, default="")
    postback_text: str = ib(metadata={"json": "postback_text"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")
    type: str = ib(metadata={"json": "type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        description_objt = None
        postback_text_objt = None
        title_objt = None
        type_objt = None

        if data.get("description", {}):
            description_objt = data.get("description", "")

        if data.get("postback_text", {}):
            postback_text_objt = data.get("postback_text", "")

        if data.get("title", {}):
            title_objt = data.get("title", "")

        if data.get("type", {}):
            type_objt = data.get("type", "")

        return cls(
            description=description_objt,
            postback_text=postback_text_objt,
            title=title_objt,
            type=type_objt,
        )


@dataclass
class ParserSectionInteractiveMessage(SerializableAttrs):
    """
    Contains the information of the sections of the interactive message.

    - options: A list of the diferents options of the section.
    - subtitle: The subtitle of the section.
    - title: The title of the section.
    """

    options: list[OptionsInteractiveMessage] = ib(metadata={"json": "options"}, default=[])
    subtitle: str = ib(metadata={"json": "subtitle"}, default="")
    title: str = ib(metadata={"json": "title"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        options_list = []
        subtitle_objt = None
        title_objt = None

        if data.get("options", []):
            options_list = [
                OptionsInteractiveMessage(**option.__dict__) for option in data.get("options", [])
            ]

        if data.get("subtitle", {}):
            subtitle_objt = data.get("subtitle", "")

        if data.get("title", {}):
            title_objt = data.get("title", "")

        return cls(
            options=options_list,
            subtitle=subtitle_objt,
            title=title_objt,
        )


@dataclass
class OptionsInteractiveMessage(SerializableAttrs):
    """
    Contains the information of the buttons of the interactive message.

    - title: The title of the button.
    - type: The type of the button.
    """

    title: str = ib(metadata={"json": "title"}, default="")
    type: str = ib(metadata={"json": "type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        title_objt = None
        type_objt = None

        if data.get("title", {}):
            title_objt = data.get("title", "")

        if data.get("type", {}):
            type_objt = data.get("type", "")

        return cls(
            title=title_objt,
            type=type_objt,
        )


@dataclass
class ContentInteractiveMessage(SerializableAttrs):
    """
    Contains the information of the content of the interactive message sended from menuflow rete.

    - caption: The footer of the interactive message.
    - header: The header of the interactive message.
    - text: The body of the interactive message.
    - type: The type of the interactive message.
    - url: The url of the interactive message if the interactive message is a media message.
    """

    caption: str = ib(metadata={"json": "caption"}, default="")
    header: str = ib(metadata={"json": "header"}, default="")
    text: str = ib(metadata={"json": "text"}, default="")
    type: str = ib(metadata={"json": "type"}, default="")
    url: str = ib(metadata={"json": "url"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        caption_objt = None
        header_objt = None
        text_objt = None
        type_objt = None
        url_objt = None

        if data.get("caption", {}):
            caption_objt = data.get("caption", "")

        if data.get("header", {}):
            header_objt = data.get("header", "")

        if data.get("text", {}):
            text_objt = data.get("text", "")

        if data.get("type", {}):
            type_objt = data.get("type", "")

        if data.get("url", {}):
            url_objt = data.get("url", "")

        return cls(
            caption=caption_objt,
            header=header_objt,
            text=text_objt,
            type=type_objt,
            url=url_objt,
        )


@dataclass
class ParserInteractiveButtonsMessage(InteractiveMessage):
    """
    Contains the information of the interactive button message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.
    """

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        action_obj = None
        body_obj = None
        footer_obj = None
        content_obj = None
        options_list = []
        interactive_type = data.get("type", "")

        # We use the same structure in gupshup and cloud for send interactive messages,
        # this structure containt the necesary information for the interactive message in the
        # content object and the options list, so we need to transform the interactive message
        # object from our structure to the cloud structure.
        if data.get("content", {}):
            content_obj = ContentInteractiveMessage.from_dict(data.get("content", {}))
            body_obj = TextReply(text=content_obj.text)
            footer_obj = TextReply(text=content_obj.caption)
            match content_obj.type:
                case "text":
                    header_obj = HeaderQuickReply(type=content_obj.type, text=content_obj.header)
                case "image":
                    header_obj = HeaderQuickReply(
                        type=content_obj.type,
                        image=MediaQuickReply(link=content_obj.url),
                    )
                case "video":
                    header_obj = HeaderQuickReply(
                        type=content_obj.type,
                        video=MediaQuickReply(link=content_obj.url),
                    )
                case "document":
                    header_obj = HeaderQuickReply(
                        type=content_obj.type,
                        document=DocumentQuickReply(link=content_obj.url, filename="Document"),
                    )

        if data.get("options", []):
            options_list = [
                OptionsInteractiveMessage(**option.__dict__) for option in data.get("options", [])
            ]

            if data.get("type", "") == "quick_reply":
                interactive_type = "button"
                buttons = []

                for option in options_list:
                    buttons.append(
                        ButtonsQuickReply.from_dict(
                            {
                                "reply": {"id": option.title, "title": option.title},
                                "type": "reply",
                            }
                        )
                    )

                action_obj = ActionQuickReply.from_dict({"buttons": buttons})

        return cls(
            type=interactive_type,
            header=header_obj,
            body=body_obj,
            footer=footer_obj,
            action=action_obj,
        )


@dataclass
class GlobalButtons(SerializableAttrs):
    """
    Contains the information of the global buttons of the interactive message.

    - title: The title of the button.
    - type: The type of the button.
    """

    title: str = ib(metadata={"json": "title"}, default="")
    type: str = ib(metadata={"json": "type"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        title_objt = None
        type_objt = None

        if data.get("title", {}):
            title_objt = data.get("title", "")

        if data.get("type", {}):
            type_objt = data.get("type", "")

        return cls(
            title=title_objt,
            type=type_objt,
        )


class ParserInteractiveListsMessage(InteractiveMessage):
    """
    Contains the information of the interactive list message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.
    """

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        action_obj = None
        body_obj = None
        global_button_obj = None
        global_button = ""
        list_items = [ParserSectionInteractiveMessage]
        interactive_type = data.get("type", "")

        if data.get("title", ""):
            header_obj = HeaderQuickReply(type="text", text=data.get("title"))

        if data.get("body", ""):
            body_obj = TextReply(text=data.get("body"))

        if data.get("global_buttons", []):
            global_button_obj = GlobalButtons.from_dict(data.get("global_buttons", [])[0])
            global_button = global_button_obj.title

        if data.get("items", []):
            list_items = [
                ParserSectionInteractiveMessage(**item.__dict__) for item in data.get("items", [])
            ]

        if global_button and list_items:
            # We use the same structure in gupshup and cloud for send interactive messages,
            # this structure containt the necesary information for the interactive message in the
            # items list and the rows list, so we need to transform the interactive message
            # object from our structure to the cloud structure.
            list_section: List[SectionsQuickReply] = []

            for item in list_items:
                list_rows: List[RowSection] = [
                    RowSection.from_dict(
                        {
                            "id": option.postback_text,
                            "title": option.title,
                            "description": option.description,
                        }
                    )
                    for option in item.options
                ]

                list_section.append(
                    SectionsQuickReply.from_dict({"title": item.title, "rows": list_rows})
                )

            action_obj = ActionQuickReply.from_dict(
                {"button": global_button, "sections": list_section}
            )

        return cls(
            type=interactive_type,
            header=header_obj,
            body=body_obj,
            action=action_obj,
        )


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
        interactive_message_obj: (
            ParserInteractiveButtonsMessage | ParserInteractiveListsMessage | InteractiveMessage
        ) = None
        interactive_message_data = data.get("interactive_message", {})

        if interactive_message_data.get("content", {}):
            interactive_message_obj = ParserInteractiveButtonsMessage.from_dict(
                interactive_message_data
            )
        elif interactive_message_data.get("global_buttons", {}):
            interactive_message_obj = ParserInteractiveListsMessage.from_dict(
                interactive_message_data
            )
        elif interactive_message_data:
            interactive_message_obj = InteractiveMessage.from_dict(interactive_message_data)

        return cls(
            body=data.get("body", ""),
            interactive_message=interactive_message_obj,
            msgtype=data.get("msgtype", ""),
        )
