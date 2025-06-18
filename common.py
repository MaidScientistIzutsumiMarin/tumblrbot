import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install


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
