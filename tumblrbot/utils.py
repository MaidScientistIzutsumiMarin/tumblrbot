from dataclasses import dataclass
from random import choice
from typing import ClassVar, Self, override

from openai import OpenAI
from rich._spinners import SPINNERS
from rich.console import RenderableType
from rich.live import Live
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import TextType

from tumblrbot.settings import Config
from tumblrbot.tumblr import TumblrClient


class PreviewLive(Live):
    def __init__(self) -> None:
        super().__init__()

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


@dataclass
class PreviewUtil:
    config: ClassVar = Config()  # pyright: ignore[reportCallIssue]

    openai: OpenAI
    tumblr: TumblrClient


def yes_no_prompt(prompt: TextType) -> bool:
    yes_option = "Y"
    no_option = "n"
    answer = Prompt.ask(prompt, choices=[yes_option, no_option], case_sensitive=False, default=no_option)
    return answer == yes_option
