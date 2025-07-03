from typing import Annotated, Any, Literal, override

from openai import BaseModel
from pydantic import ConfigDict, PlainSerializer
from pydantic.json_schema import SkipJsonSchema
from rich.panel import Panel


class FullyValidatedModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_default=True,
        validate_return=True,
        validate_by_name=True,
    )


class Post(FullyValidatedModel):
    class Block(FullyValidatedModel):
        type: str = "text"
        text: str = ""
        blocks: set[int] = set()  # noqa: RUF012

    tags: Annotated[list[str], PlainSerializer(",".join)] = []  # noqa: RUF012
    content: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    layout: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    trail: SkipJsonSchema[list[Any]] = []  # noqa: RUF012
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "draft"
    timestamp: SkipJsonSchema[int] = 0
    is_submission: SkipJsonSchema[bool] = False

    def __rich__(self) -> Panel:
        return Panel(
            self.get_text_content(),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        indices: set[int] = set()
        for block in self.layout:
            if block.type == "ask":
                indices |= block.blocks

        self.content = [block for i, block in enumerate(self.content) if i not in indices and block.type == "text"]

    def get_text_content(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: str
        content: str

    messages: list[Message]
