from abc import abstractmethod
from dataclasses import dataclass
from locale import localize
from random import choice
from typing import TYPE_CHECKING, ClassVar

from openai import OpenAI  # noqa: TC002
from rich._spinners import SPINNERS
from rich.live import Live
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

from tumblrbot.utils.models import Config
from tumblrbot.utils.tumblr import TumblrSession  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import RenderableType


@dataclass(frozen=True)
class FlowClass:
    config: ClassVar = Config.load()

    openai: OpenAI
    tumblr: TumblrSession

    @abstractmethod
    def main(self) -> None: ...

    def get_data_paths(self) -> list[Path]:
        return list(map(self.get_data_path, self.config.download_blog_identifiers))

    def get_data_path(self, blog_identifier: str) -> Path:
        return (self.config.data_directory / blog_identifier).with_suffix(".jsonl")


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

        self.custom_update()

    def custom_update(self, *renderables: RenderableType | None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        table.add_row(*renderables)
        self.update(table)


def localize_number(value: object) -> str:
    return localize(str(value), grouping=True)
