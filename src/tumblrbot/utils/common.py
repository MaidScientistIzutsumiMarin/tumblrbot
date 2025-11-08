from abc import abstractmethod
from random import choice
from typing import TYPE_CHECKING, ClassVar, Self, override

from pydantic import ConfigDict
from rich._spinners import SPINNERS
from rich.live import Live
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

from tumblrbot.utils.models import Config, FullyValidatedModel

if TYPE_CHECKING:
    from pathlib import Path

    from openai import OpenAI
    from rich.console import RenderableType

    from tumblrbot.utils.tumblr import TumblrSession


class FlowClass(FullyValidatedModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    @override
    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def custom_update(self, *renderables: RenderableType | None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        table.add_row(*renderables)
        self.update(table)
