import sys
from collections.abc import Callable

from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install


def run_main(name: str, main: Callable[[], str | int | None]) -> None:
    if name == "__main__":
        try:
            install(show_locals=True)
            sys.exit(main())
        except SystemExit:
            raise
        except BaseException:
            Console(stderr=True, style="logging.level.error").print_exception()
            raise
        finally:
            Prompt.ask("Press Enter to close")
