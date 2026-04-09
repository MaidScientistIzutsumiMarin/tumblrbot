from locale import localize

from rich.console import Console

console = Console()
warning_console = Console(stderr=True, style="logging.level.warning")
error_console = Console(stderr=True, style="logging.level.error")


def localize_number(value: object) -> str:
    return localize(str(value), grouping=True)
