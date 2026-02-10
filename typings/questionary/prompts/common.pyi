from collections.abc import Callable

class Choice[T]:
    def __init__(
        self,
        title: str | list[tuple[str, str]] | list[tuple[str, str, Callable[[object], None]]] | None,
        value: T | None = None,
        disabled: str | None = None,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
