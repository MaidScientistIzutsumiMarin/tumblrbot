import sys
from collections.abc import Callable
from pathlib import Path
from random import choice
from typing import Self, override

from pydantic import BaseModel
from rich._spinners import SPINNERS
from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.traceback import install


class Tags(BaseModel):
    tags: list[str]

    @override
    def __str__(self) -> str:
        return " ".join(f"#{tag}" for tag in self.tags)


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

        self.custom_update("")

    @override
    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def custom_update(self, body: RenderableType, tags: Tags | None = None) -> None:
        table = Table.grid()
        table.add_row(self.progress)
        if body:
            table.add_row(Panel(body, title="Preview", subtitle=str(tags or ""), subtitle_align="left"))

        return self.update(table)


def run_main(name: str, main: Callable[[], str | int | None]) -> None:
    if name == "__main__":
        # It seems like calling 'python script.py' will use the relative path to the script.
        # Meanwhile, double-clicking or calling the script directly will use an absolute path to the script.
        # So, this is currently the only way we know to tell if the console window will close after running.
        # Not sure how reliable this is, especially across platforms, but it should work for now.
        console_auto_closes = Path(sys.argv[0]).is_absolute()

        try:
            install(show_locals=True)
            sys.exit(main())
        except SystemExit:
            raise
        except BaseException:
            if console_auto_closes:
                Console(stderr=True, style="logging.level.error").print_exception()
            raise
        finally:
            if console_auto_closes:
                Prompt.ask("Press Enter to close")
