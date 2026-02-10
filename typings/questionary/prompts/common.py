from collections.abc import Callable  # noqa: INP001
from typing import Any

FormattedText = str | list[tuple[str, str]] | list[tuple[str, str, Callable[[Any], None]]] | None


class Choice[T]:
    def __init__(  # noqa: PLR0913
        self,
        title: FormattedText,
        value: T | None = None,
        disabled: str | None = None,
        *,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
