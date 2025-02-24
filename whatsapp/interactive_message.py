from typing import Dict, List

from attr import dataclass, ib
from mautrix.types import BaseMessageEventContent, SerializableAttrs, MessageType, Obj


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
class InteractiveMedia(SerializableAttrs):
    """
    Contains the information of the media header.

    - link: The link of the media.
    """

    link: str = ib(metadata={"json": "link"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        if not data.get("link"):
            return None

        return cls(
            link=data.get("link", ""),
        )


@dataclass
class InteractiveDocumentMedia(InteractiveMedia):
    """
    Contains the information of the document header.

    - link: The link of the document.
    - filename: The filename of the document.
    """

    filename: str = ib(metadata={"json": "filename"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        interactiveMedia = super().from_dict(data)

        if not interactiveMedia:
            return None

        return cls(
            link=interactiveMedia.link,
            filename=data.get("filename", "Document"),
        )


@dataclass
class InteractiveHeader(SerializableAttrs):
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
    image: InteractiveMedia = ib(metadata={"json": "image"}, default={})
    video: InteractiveMedia = ib(metadata={"json": "video"}, default={})
    document: InteractiveDocumentMedia = ib(metadata={"json": "document"}, default={})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            type=data.get("type", ""),
            text=data.get("text", ""),
            video=InteractiveMedia.from_dict(data.get("video", {})),
            document=InteractiveDocumentMedia.from_dict(data.get("document", {})),
            image=InteractiveMedia.from_dict(data.get("image", {})),
        )

    def _get_media_and_type(self):
        """
        Return the media object of the header and his type.
        """
        match self.type:
            case "image":
                return self.image, MessageType.IMAGE
            case "video":
                return self.video, MessageType.VIDEO
            case "document":
                return self.document, MessageType.FILE
            case _:
                return None, MessageType.TEXT

    def get_media_name(self):
        """
        Get the name of the media file.
        """
        media, _ = self._get_media_and_type()

        if not isinstance(media, InteractiveDocumentMedia):
            return ""

        return media.filename

    def get_media_link(self):
        """
        Get the link of the media file.
        """
        media, _ = self._get_media_and_type()
        return media.link if media else ""

    def get_media_type(self):
        """
        Get the type of the media file.
        """
        _, media_type = self._get_media_and_type()
        return media_type


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
class InteractiveReplyContent(SerializableAttrs):
    """
    Contains the information of the header, body and footer of the interactive message.
    This class is used to transform the interactive message object from menuflow rete to the
    interactive message object of whatsapp cloud.

    - header: The header of the interactive message.
    - body: The body of the interactive message.
    - footer: The footer of the interactive message.
    """

    header: InteractiveHeader = ib(factory=InteractiveHeader, metadata={"json": "header"})
    body: TextReply = ib(factory=TextReply, metadata={"json": "body"})
    footer: TextReply = ib(factory=TextReply, metadata={"json": "footer"})

    @classmethod
    def from_dict(cls, data: dict):
        header_obj: InteractiveHeader = cls()._translate_header(data=data)
        body_obj = TextReply(text=data.get("text", ""))
        footer_obj = TextReply(text=data.get("caption", ""))

        return cls(
            header=header_obj,
            body=body_obj,
            footer=footer_obj,
        )

    def _get_media_data(self, data: dict) -> dict:
        """
        Get the media data from the interactive message object of menuflow rete.
        """
        header_data = data.get("header")
        link = ""
        filename = "Document"

        if data.get("url"):
            link = data.get("url", "")
        elif isinstance(header_data, Obj):
            link = header_data.get("link", "")

        media_data = {
            "link": link,
        }

        if data.get("type", "") == "document":
            if isinstance(header_data, dict):
                filename = header_data.get("filename", "")

            media_data["filename"] = filename

        # This structure is used in the cloud for send interactive media messages, this structure
        # is like: {"type": "image", "image": {"link": "https://example.com/image.jpg"}}
        interactive_header_data = {
            "type": data.get("type", ""),
            data.get("type", ""): media_data,
        }

        return interactive_header_data

    def _translate_header(self, data: dict) -> InteractiveHeader:
        """
        Translate the header of the interactive message from menuflow rete to the interactive
        message object of whatsapp cloud.
        """
        # We use the same structure in gupshup and cloud for send interactive messages,
        # this structure containt the necesary information for the interactive message in the
        # content object and the options list, so we need to transform the interactive message
        # object from our structure to the cloud structure
        header_obj = None
        match data.get("type", ""):
            case "image" | "video" | "document":
                interactive_header_data = self._get_media_data(data)
                import logging

                logging.getLogger().critical(f"data: {data}")
                logging.getLogger().critical(f"interactive_header_data: {interactive_header_data}")
                header_obj = InteractiveHeader.from_dict(interactive_header_data)

            case "text":
                header_data = {
                    "type": data.get("type", ""),
                    data.get("type", ""): data.get("header", ""),
                }
                header_obj: InteractiveHeader = InteractiveHeader.from_dict(header_data)

        return header_obj


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
    flow_action_payload: str = ib(metadata={"json": "flow_action_payload"}, default="{}")

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


@dataclass
class InteractiveMessage(SerializableAttrs):
    """
    Contains the information from the interactive buttons message.

    - type: The type of the interactive message.

    - header: The information of the interactive header message.

    - body: The information of the interactive body message.

    - footer: The information of the interactive footer message.
    """

    type: str = ib(metadata={"json": "type"}, default="")
    header: InteractiveHeader = ib(metadata={"json": "header"}, default={})
    body: TextReply = ib(metadata={"json": "body"}, default={})
    footer: TextReply = ib(metadata={"json": "footer"}, default={})
    action: ActionQuickReply | ActionFlowReply | ActionListReply = ib(
        metadata={"json": "action"}, default={}
    )

    @classmethod
    def from_dict(cls, data: dict):
        header_obj = None
        body_obj = None
        footer_obj = None

        if data.get("header", {}):
            header_obj = InteractiveHeader.from_dict(data.get("header", {}))

        if data.get("body", {}):
            body_obj = TextReply.from_dict(data.get("body", {}))

        if data.get("footer", {}):
            footer_obj = TextReply.from_dict(data.get("footer", {}))

        return cls(type=data.get("type", ""), header=header_obj, body=body_obj, footer=footer_obj)

    def body_message(self) -> str:
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
class InteractiveButtonsMessage(InteractiveMessage):
    """
    Contains the information of the interactive button message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.

    - action: The information of the interactive button message.|
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

    def body_message(self) -> str:
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
        msg: dict[str, str | list] = {
            "header": self.header.text if self.header else "",
            "body": self.body.text if self.body else "",
            "footer": self.footer.text if self.footer else "",
            "buttons": [],
        }

        for index, button in enumerate(self.action.buttons, start=1):
            msg["buttons"].append(
                {
                    "id": button.reply.id,
                    "index": index,
                    "title": button.reply.title,
                }
            )
        return msg


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

    def body_message(self) -> str:
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
        payload: dict = {}

        if self.action.parameters.flow_action_payload:
            payload = self.action.parameters.flow_action_payload.serialize()

        msg: dict[str, str | list] = {
            "header": self.header.text if self.header else "",
            "body": self.body.text if self.body else "",
            "footer": self.footer.text if self.footer else "",
            "flow": {
                "parameters": {
                    "flow_name": self.action.parameters.flow_name,
                    "button": self.action.parameters.flow_cta,
                    "payload": payload,
                }
            },
        }

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


class InteractiveListsMessage(InteractiveMessage):
    """
    Contains the information of the interactive list message that is sended from menuflow rete.

    It is a subclass of InteractiveMessage that transforms the interactive message object from
    menuflow rete to the interactive message object of whatsapp cloud.

    - action: The information of the interactive list message.
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
            header_obj = InteractiveHeader(type="text", text=data.get("title"))

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

            action_obj: ActionListReply = ActionListReply.from_dict(
                {"button": global_button, "sections": list_section}
            )

        import logging

        logging.getLogger().critical(f"action_obj<<<<<<<<: {action_obj}")

        return cls(
            type=interactive_type,
            header=header_obj,
            body=body_obj,
            action=action_obj,
        )

    def body_message(self) -> str:
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
        msg: dict[str, str | list] = {
            "header": self.header.text if self.header else "",
            "body": self.body.text if self.body else "",
            "footer": self.footer.text if self.footer else "",
            "sections": [],
        }

        for section_index, section in enumerate(self.action.sections, start=1):
            for row_index, row in enumerate(section.rows, start=1):
                msg["sections"].append(
                    {
                        "title": section.title,
                        "section_index": section_index,
                        "row_title": row.title,
                        "row_description": row.description,
                        "row_id": row.id,
                        "row_index": row_index,
                    }
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
    interactive_message: (
        InteractiveButtonsMessage
        | InteractiveFlowMessage
        | InteractiveListsMessage
        | InteractiveMessage
    ) = ib(metadata={"json": "interactive_message"}, default={})
    msgtype: str = ib(metadata={"json": "msgtype"}, default="")

    @classmethod
    def from_dict(cls, data: dict):
        interactive_message_obj: (
            InteractiveButtonsMessage
            | InteractiveFlowMessage
            | InteractiveListsMessage
            | InteractiveMessage
        ) = None
        interactive_message_data = data.get("interactive_message", {})

        match interactive_message_data.get("type"):
            case "quick_reply":
                interactive_message_obj = InteractiveButtonsMessage.from_dict(
                    interactive_message_data
                )
            case "list":
                interactive_message_obj = InteractiveListsMessage.from_dict(
                    interactive_message_data
                )
            case "flow":
                interactive_message_obj = InteractiveFlowMessage.from_dict(
                    interactive_message_data
                )
            case _:
                interactive_message_obj = InteractiveMessage.from_dict(interactive_message_data)

        return cls(
            body=data.get("body", ""),
            interactive_message=interactive_message_obj,
            msgtype=data.get("msgtype", ""),
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
