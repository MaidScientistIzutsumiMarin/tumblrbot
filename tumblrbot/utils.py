from random import choice
from typing import IO, Literal, Self, overload, override

import rich
from pydantic import BaseModel, ConfigDict, Secret
from rich._spinners import SPINNERS
from rich.console import RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import TextType


class Post(BaseModel):
    model_config = ConfigDict(extra="allow")

    class Content(BaseModel):
        model_config = ConfigDict(extra="allow")

        type: str
        text: str = ""

    type ContentList = list[Content]
    type TagList = list[str]

    content: ContentList
    tags: TagList
    trail: list[object] = []
    timestamp: int = 0

    def __rich__(self) -> Panel:
        renderable = self.get_text_content()
        subtitle = " ".join(f"#{tag}" for tag in self.tags)
        return Panel(renderable, title="Preview", subtitle=subtitle, subtitle_align="left")

    def get_text_content(self) -> str:
        return "\n\n".join(block.text for block in self.content if block.type == "text")


class PreviewLive(Live):
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

    def custom_update(self, *renderables: RenderableType | None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        table.add_row(*renderables)
        return self.update(table)


def yes_no_prompt(prompt: TextType) -> bool:
    yes_option = "Y"
    no_option = "n"
    answer = Prompt.ask(prompt, choices=[yes_option, no_option], case_sensitive=False, default=no_option)
    return answer == yes_option


@overload
def token_prompt(token_type: str) -> str: ...
@overload
def token_prompt(token_type: str, *, secret: Literal[True]) -> Secret[str]: ...
def token_prompt(token_type: str, *, secret: bool = False) -> Secret[str] | str:
    prompt = f"Enter your [cyan]{token_type}"
    if secret:
        prompt += " [yellow](hidden)"

    token = Prompt.ask(prompt, password=secret).strip()
    if secret:
        return Secret(token)
    return token


def print_prompt(url: str, *token_types: str) -> None:
    token_types_string = " and ".join(f"[cyan]{token_type}[/]" for token_type in token_types)
    rich.print(f"Retrieve your {token_types_string} from: {url}")


def dump_model(model: BaseModel, fp: IO[bytes]) -> int:
    return fp.write(model.__pydantic_serializer__.to_json(model) + b"\n")
