from collections.abc import Generator
from itertools import chain
from pathlib import Path
from random import choice
from textwrap import dedent
from typing import Self, override

import rich
from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator
from pydantic.json_schema import SkipJsonSchema
from rich._spinners import SPINNERS
from rich.console import RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import TextType

from tumblrbot.settings import CONFIG


class ConfiguredModel(BaseModel):
    model_config = ConfigDict(validate_default=True)


class Post(ConfiguredModel):
    class ContentBlock(ConfiguredModel):
        type: SkipJsonSchema[str] = "text"
        text: str = ""

    class LayoutBlock(ConfiguredModel):
        type: str
        blocks: list[int] = []

    timestamp: SkipJsonSchema[NonNegativeInt] = 0
    is_submission: SkipJsonSchema[bool] = False
    tags: list[str]
    content: list[ContentBlock]
    layout: SkipJsonSchema[list[LayoutBlock]] = []
    trail: SkipJsonSchema[list[object]] = []

    @staticmethod
    def get_posts_path(blog_name: str) -> Path:
        return (CONFIG.training.data_directory / blog_name).with_suffix(".jsonl")

    @classmethod
    def get(cls) -> Generator[Self]:
        for blog_name in CONFIG.training.blog_names:
            with cls.get_posts_path(blog_name).open(encoding="utf_8") as fp:
                for line in fp:
                    yield cls.model_validate_json(line)

    def __rich__(self) -> Panel:
        return Panel(
            self.get_text_content(),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    @model_validator(mode="after")
    def filter_content(self) -> Self:
        ask_blocks = {*chain.from_iterable(block.blocks for block in self.layout if block.type == "ask")}
        self.content = [block for i, block in enumerate(self.content) if i not in ask_blocks and block.type == "text"]
        return self

    def get_text_content(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class PreviewLive(Live):
    def __init__(self, *, transient: bool = False) -> None:
        super().__init__(transient=transient)

        spinner_name = choice(list(SPINNERS))
        self.progress = Progress(
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            MofNCompleteColumn(),
            SpinnerColumn(spinner_name),
            auto_refresh=False,
        )

        self.custom_update()

    @override
    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def custom_update(self, *renderables: RenderableType | None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        table.add_row(*renderables)
        self.update(table)


def yes_no_prompt(prompt: TextType) -> bool:
    yes_option = "Y"
    no_option = "n"
    answer = Prompt.ask(prompt, choices=[yes_option, no_option], case_sensitive=False, default=no_option)
    return answer == yes_option


def token_prompt(url: object, *tokens: object) -> Generator[str]:
    token_strings = [f"[cyan]{token}[/]" for token in tokens]
    url_prompt_tokens = " and ".join(token_strings)

    rich.print(f"Retrieve your {url_prompt_tokens} from: {url}")
    for token in token_strings:
        prompt = f"Enter your [cyan]{token}"
        yield Prompt.ask(prompt).strip()

    rich.print()


def dedent_print(text: str) -> None:
    rich.print(dedent(text).lstrip())
