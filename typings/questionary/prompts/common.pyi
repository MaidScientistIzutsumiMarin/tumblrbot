from collections.abc import Callable

type FormattedText = str | list[tuple[str, str]] | list[tuple[str, str, Callable[[object], None]]] | None

class Choice[T]:
    def __init__(
        self,
        title: FormattedText,
        value: T | None = None,
        disabled: str | None = None,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
