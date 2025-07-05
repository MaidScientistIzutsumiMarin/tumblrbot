from typing import Any, Literal, override

from openai import BaseModel
from pydantic import ConfigDict
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
        type: str = ""
        text: str = ""
        blocks: list[int] = []  # noqa: RUF012

    timestamp: SkipJsonSchema[int] = 0
    tags: list[str] = []  # noqa: RUF012
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "published"

    content: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    layout: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    trail: SkipJsonSchema[list[Any]] = []  # noqa: RUF012

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
                indices.update(block.blocks)

        self.content = [block for i, block in enumerate(self.content) if i not in indices and block.type == "text"]

    def get_text_content(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
