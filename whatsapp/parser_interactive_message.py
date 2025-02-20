from email import header
from typing import List

from attr import dataclass, ib
from mautrix.types import SerializableAttrs

from whatsapp.interactive_message import (
    ButtonsQuickReply,
    DocumentQuickReply,
    HeaderQuickReply,
    MediaQuickReply,
    RowSection,
    SectionsQuickReply,
    TextReply,
)
from whatsapp_matrix.config import Config


@dataclass
class ActionReply(SerializableAttrs):
    """
    Contains the action section of the interactive message.

    - name: The name of the action message.
    """

    name: str = ib(metadata={"json": "name"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data.get("name", ""),
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

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        body_obj = None
        footer_obj = None

        if data.get("header", {}):
            header_obj = HeaderQuickReply.from_dict(data.get("header", {}))

        if data.get("body", {}):
            body_obj = TextReply.from_dict(data.get("body", {}))

        if data.get("footer", {}):
            footer_obj = TextReply.from_dict(data.get("footer", {}))

        return cls(
            type=data.get("type", ""),
            header=header_obj,
            body=body_obj,
            footer=footer_obj,
        )

    def body_message(self, config: Config) -> str:
        """
        Obtain a message text with the information of the interactive body message.

        Params
        ------
        config: Config
            The configuration of the bridge.

        Returns
        -------
        str
            The message text with the information of the interactive body message.
        """
        return None


@dataclass
class OptionsInteractiveMessage(SerializableAttrs):
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
class SectionInteractiveMessage(SerializableAttrs):
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
class InteractiveReplyContent(ContentInteractiveMessage):
    """
    Contains the information of the header, body and footer of the interactive message.
    This class is used to transform the interactive message object from menuflow rete to the
    interactive message object of whatsapp cloud.

    - header: The header of the interactive message.
    - body: The body of the interactive message.
    - footer: The footer of the interactive message.
    """

    header: HeaderQuickReply = ib(factory=HeaderQuickReply, metadata={"json": "header"})
    body: TextReply = ib(factory=TextReply, metadata={"json": "body"})
    footer: TextReply = ib(factory=TextReply, metadata={"json": "footer"})

    @classmethod
    def from_dict(cls, data: dict):
        # We use the same structure in gupshup and cloud for send interactive messages,
        # this structure containt the necesary information for the interactive message in the
        # content object and the options list, so we need to transform the interactive message
        # object from our structure to the cloud structure.
        content_obj = super().from_dict(data)
        body_obj = TextReply(text=content_obj.text)
        footer_obj = TextReply(text=content_obj.caption)
        header_obj = None
        match content_obj.type:
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
            case "text":
                header_obj = HeaderQuickReply(type=content_obj.type, text=content_obj.header)

        return cls(
            header=header_obj,
            body=body_obj,
            footer=footer_obj,
        )


@dataclass
class ActionQuickReply(ActionReply):
    """
    Contains the buttons of the interactive message.

    - buttons: The information of the buttons in a quick reply message.
    """

    buttons: List[ButtonsQuickReply] = ib(factory=List, metadata={"json": "buttons"})

    @classmethod
    def from_dict(cls, data: dict):
        button_obj = None

        if data.get("buttons", []):
            button_obj = [
                ButtonsQuickReply(**button.__dict__) for button in data.get("buttons", [])
            ]

        return cls(
            name=data.get("name", ""),
            buttons=button_obj,
        )


@dataclass
class InteractiveButtonsMessage(InteractiveMessage):
    """
    Contains the information of the interactive button message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.
    """

    action: ActionQuickReply = ib(metadata={"json": "action"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        action_obj = None
        reply_content = None
        options_list = []
        interactive_type = data.get("type", "")

        if data.get("content", {}):
            reply_content = InteractiveReplyContent.from_dict(data.get("content", {}))

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
            header=reply_content.header,
            body=reply_content.body,
            footer=reply_content.footer,
            action=action_obj,
        )

    def body_message(self, config: Config) -> str:
        """
        Obtain a message text with the information of the interactive quick reply message.

        Params
        ------
        config: Config
            The configuration of the bridge.

        Returns
        -------
        str
            The message text with the information of the interactive quick reply message.
        """
        button_item_format = config.get("bridge.interactive_messages.button_message")
        msg = f"""{self.header.text if self.header else ''}
            {self.body.text  if self.body else ''}
            {self.footer.text  if self.footer else ''}
        """
        message: str = button_item_format or ""
        for index, button in enumerate(self.action.buttons, start=1):
            msg += message.format(index=index, title=button.reply.title, id=button.reply.id)
        return msg


@dataclass
class ParameterFlowReply(SerializableAttrs):
    """
    Contains the parameters of the interactive flow message.

    - flow_message_version: The version of the interactive flow message.
    - flow_name: The name of the interactive flow message.
    - flow_cta: The button to call to action of the interactive flow message.
    - flow_action: The action of the interactive flow message.
    - flow_token: The token of the interactive flow message.
    - flow_action: The action of the interactive flow message (navigate, data_exchange)
    - flow_action_payload: The payload of the interactive flow message, this payload is used when
        the action is navigate, otherwise it is empty.
    """

    flow_message_version: str = ib(metadata={"json": "flow_message_version"}, default="")
    flow_name: str = ib(metadata={"json": "flow_name"}, default="")
    flow_cta: str = ib(metadata={"json": "flow_cta"}, default="")
    flow_token: str = ib(metadata={"json": "flow_token"}, default="")
    flow_action: str = ib(metadata={"json": "flow_action"}, default="")
    flow_action_payload: str = ib(metadata={"json": "flow_action_payload"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            flow_message_version=data.get("message_version", "3"),
            flow_name=data.get("name", ""),
            flow_cta=data.get("button", ""),
            flow_token=data.get("token", ""),
            flow_action=data.get("action", ""),
            flow_action_payload=data.get("payload", ""),
        )


@dataclass
class ActionFlowReply(ActionReply):
    """
    Contains the information of the interactive flow message.

    - parameters: The parameters of the interactive flow message.

    """
    parameters: ParameterFlowReply = ib(
        factory=ParameterFlowReply, metadata={"json": "parameters"}
    )

    @classmethod
    def from_dict(cls, data: dict):

        parameters_obj: ParameterFlowReply = ParameterFlowReply.from_dict(
            data.get("parameters", {})
        )

        return cls(
            name=data.get("name", "flow"),
            parameters=parameters_obj,
        )


@dataclass
class InteractiveFlowMessage(InteractiveMessage):
    """
    Contains the information of the interactive flow message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.

    - action: The information of the interactive flow message.
    """

    action: ActionFlowReply = ib(metadata={"json": "action"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        action_obj = None
        reply_content = None
        interactive_type = data.get("type", "")

        if data.get("content", {}):
            reply_content = InteractiveReplyContent.from_dict(data.get("content", {}))

        if data.get("action"):
            action_obj: ActionFlowReply = ActionFlowReply.from_dict(data.get("action", {}))

        return cls(
            type=interactive_type,
            header=reply_content.header,
            body=reply_content.body,
            footer=reply_content.footer,
            action=action_obj,
        )

    def body_message(self, config: Config) -> str:
        """
        Obtain a message text with the information of the interactive flow message.

        Params
        ------
        config: Config
            The configuration of the bridge.

        Returns
        -------
        str
            The message text with the information of the interactive flow message.
        """
        msg = f"""{self.header.text if self.header else ''}
            {self.body.text  if self.body else ''}
            {self.footer.text  if self.footer else ''}
            {self.action.name}
        """
        return msg


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


@dataclass
class ActionListReply(ActionReply):
    """
    Contains the buttons of the interactive message.

    - button: The name of the button in a list message.

    - sections: The information of the sections in a list message.
    """

    button: str = ib(metadata={"json": "button"}, default="")
    sections: List[SectionsQuickReply] = ib(factory=List, metadata={"json": "sections"})

    @classmethod
    def from_dict(cls, data: dict):
        section_obj = None

        if data.get("sections", []):
            section_obj = [
                SectionsQuickReply(**section.__dict__) for section in data.get("sections", [])
            ]

        return cls(
            name=data.get("name", ""),
            button=data.get("button", ""),
            sections=section_obj,
        )


class InteractiveListsMessage(InteractiveMessage):
    """
    Contains the information of the interactive list message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.
    """

    action: ActionListReply = ib(metadata={"json": "action"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        action_obj = None
        body_obj = None
        global_button_obj = None
        global_button = ""
        list_items = [SectionInteractiveMessage]
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
                SectionInteractiveMessage(**item.__dict__) for item in data.get("items", [])
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

            action_obj = ActionListReply.from_dict(
                {"button": global_button, "sections": list_section}
            )

        return cls(
            type=interactive_type,
            header=header_obj,
            body=body_obj,
            action=action_obj,
        )

    def body_message(self, config: Config) -> str:
        """
        Obtain a message text with the information of the interactive list message.

        Params
        ------
        config: Config
            The configuration of the bridge.

        Returns
        -------
        str
            The message text with the information of the interactive list message.
        """
        list_item_format = config.get("bridge.interactive_messages.list_message")
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
            InteractiveButtonsMessage | InteractiveListsMessage | InteractiveMessage
        ) = None
        interactive_message_data = data.get("interactive_message", {})

        if interactive_message_data.get("type") == "quick_reply":
            interactive_message_obj = InteractiveButtonsMessage.from_dict(interactive_message_data)
        elif interactive_message_data.get("type") == "list":
            interactive_message_obj = InteractiveListsMessage.from_dict(interactive_message_data)
        elif interactive_message_data.get("type") == "flow":
            interactive_message_obj = InteractiveFlowMessage.from_dict(interactive_message_data)
        elif interactive_message_data:
            interactive_message_obj = InteractiveMessage.from_dict(interactive_message_data)

        return cls(
            body=data.get("body", ""),
            interactive_message=interactive_message_obj,
            msgtype=data.get("msgtype", ""),
        )
