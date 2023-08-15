from typing import List

from attr import dataclass, ib
from mautrix.types import SerializableAttrs


@dataclass
class QuickReplyItem(SerializableAttrs):
    content_type: str = ib(factory=str, metadata={"json": "content_type"})
    title: str = ib(factory=str, metadata={"json": "title"})
    payload: str = ib(metadata={"json": "payload"}, default=None)
    image_url: str = ib(metadata={"json": "image_url"}, default=None)


@dataclass
class QuickReply(SerializableAttrs):
    text: str = ib(factory=str, metadata={"json": "text"})
    quick_replies: List[QuickReplyItem] = ib(factory=List, metadata={"json": "quick_replies"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            text=data.get("text", None),
            quick_replies=[
                QuickReplyItem(**button.__dict__) for button in data.get("quick_replies", [])
            ],
        )

    @property
    def message(self) -> str:
        msg = f"{self.text}"
        for option in self.quick_replies:
            msg = f"{msg}\n{self.quick_replies.index(option) + 1}. {option.title}"

        return msg


@dataclass
class TemplateDefaultAction(SerializableAttrs):
    type: str = ib(factory=str, metadata={"json": "type"})
    url: str = ib(factory=str, metadata={"json": "url"})
    webview_height_ratio: str = ib(factory=str, metadata={"json": "webview_height_ratio"})


@dataclass
class TemplateButton(SerializableAttrs):
    type: str = ib(factory=str, metadata={"json": "type"})
    title: str = ib(factory=str, metadata={"json": "title"})
    url: str = ib(metadata={"json": "url"}, default=None)
    payload: str = ib(metadata={"json": "payload"}, default=None)


@dataclass
class TemplatePayloadElement(SerializableAttrs):
    title: str = ib(factory=str, metadata={"json": "title"})
    image_url: str = ib(factory=str, metadata={"json": "image_url"})
    subtitle: str = ib(factory=str, metadata={"json": "subtitle"})
    default_action: TemplateDefaultAction = ib(
        factory=TemplateDefaultAction, metadata={"json": "default_action"}
    )
    buttons: List[TemplateButton] = ib(factory=List, metadata={"json": "buttons"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data.get("title", None),
            image_url=data.get("image_url", None),
            subtitle=data.get("subtitle", None),
            default_action=TemplateDefaultAction(**data.get("default_action", {})),
            buttons=[TemplateButton(**button.__dict__) for button in data.get("buttons", [])],
        )


@dataclass
class GenericTemplatePayload(SerializableAttrs):
    template_type: str = ib(factory=str, metadata={"json": "template_type"})
    elements: List[TemplatePayloadElement] = ib(metadata={"json": "elements"}, factory=List)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            template_type=data.get("template_type", None),
            elements=[
                TemplatePayloadElement(**element.__dict__) for element in data.get("elements", [])
            ],
        )


@dataclass
class GenericTemplate(SerializableAttrs):
    type: str = ib(metadata={"json": "type"}, default="template")
    payload: GenericTemplatePayload = ib(
        factory=GenericTemplatePayload, metadata={"json": "payload"}
    )

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            type=data.get("type", None),
            payload=GenericTemplatePayload(**data.get("payload", {}).__dict__),
        )

    @property
    def message(self) -> str:
        msg = f"{self.payload.elements[0].title}\n{self.payload.elements[0].subtitle}"
        for option in self.payload.elements[0].buttons:
            msg = f"{msg}\n{self.payload.elements[0].buttons.index(option) + 1}. {option.title}"

        return msg


@dataclass
class ButtonTemplatePayload(SerializableAttrs):
    template_type: str = ib(factory=str, metadata={"json": "template_type"})
    text: str = ib(factory=str, metadata={"json": "text"})
    buttons: List[TemplateButton] = ib(factory=List, metadata={"json": "buttons"})

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            template_type=data.get("template_type", None),
            text=data.get("text", None),
            buttons=[TemplateButton(**button.__dict__) for button in data.get("buttons", [])],
        )


@dataclass
class ButtonTemplate(SerializableAttrs):
    type: str = ib(metadata={"json": "type"}, default="template")
    payload: ButtonTemplatePayload = ib(
        factory=ButtonTemplatePayload, metadata={"json": "payload"}
    )

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            type=data.get("type", None),
            payload=ButtonTemplatePayload(**data.get("payload", {}).__dict__),
        )

    @property
    def message(self) -> str:
        msg = f"{self.payload.text}\n"
        for option in self.payload.buttons:
            msg = f"{msg}\n{self.payload.buttons.index(option) + 1}. {option.title}"

        return msg
