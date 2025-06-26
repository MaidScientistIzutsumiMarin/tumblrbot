from random import choice
from typing import IO, Self, override

from pydantic import BaseModel
from rich._spinners import SPINNERS
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import TextType


class Post(BaseModel):
    class Content(BaseModel):
        type: str
        text: str | None = None

    timestamp: int
    tags: list[str]
    content: list[Content]
    trail: list[object]

    def __rich__(self) -> Panel:
        renderable = self.get_text_content()
        subtitle = " ".join(f"#{tag}" for tag in self.tags)
        return Panel(renderable, title="Preview", subtitle=subtitle, subtitle_align="left")

    def get_text_content(self) -> str:
        return "\n".join(block.text for block in self.content if block.type == "text" and block.text is not None)


class CustomLive(Live):
    def __init__(self) -> None:
        super().__init__()

        spinner_name = choice(list(SPINNERS))  # noqa: S311
        self.progress = Progress(
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            MofNCompleteColumn(),
            SpinnerColumn(spinner_name),
            auto_refresh=False,
        )

        self.custom_update(None)

    @override
    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def custom_update(self, post: Post | None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        table.add_row(post)
        return self.update(table)


def yes_no_prompt(prompt: TextType, *, default: bool = True) -> bool:
    yes_option = "y"
    no_option = "n"
    answer = Prompt.ask(prompt, choices=[yes_option, no_option], case_sensitive=False, default=yes_option if default else no_option)
    return answer == yes_option


def dump_model(model: BaseModel, fp: IO[bytes]) -> int:
    return fp.write(model.__pydantic_serializer__.to_json(model) + b"\n")
