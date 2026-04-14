from locale import localize
from random import choice
from typing import TYPE_CHECKING

from rich._spinners import SPINNERS
from rich.console import Console
from rich.live import Live
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

from tumblrbot.utils.models import Config

if TYPE_CHECKING:
    from rich.console import RenderableType


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


class TumblrBotError(Exception):
    pass


def localize_number(value: object) -> str:
    return localize(str(value), grouping=True)


config = Config.load()

console = Console()
warning_console = Console(stderr=True, style="logging.level.warning")
error_console = Console(stderr=True, style="logging.level.error")
