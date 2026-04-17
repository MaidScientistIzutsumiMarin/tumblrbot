from collections.abc import Callable
from typing import Any

type FormattedText = str | list[tuple[str, str]] | list[tuple[str, str, Callable[[Any], None]]] | None

class Choice[T]:
    def __init__(
        self,
        title: FormattedText,
        value: T,  # technically this can be None, but we don't know how to make that work with the typing...
        disabled: str | None = None,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
