from collections.abc import Callable, Sequence
from typing import Any, overload

type FormattedText = str | list[tuple[str, str]] | list[tuple[str, str, Callable[[Any], None]]] | None
type Choices[T] = Sequence[str | Choice[T] | dict[str, Any]]

class Choice[T]:
    @overload
    def __init__[U: FormattedText](
        self: Choice[U],
        title: U,
        value: None = None,
        disabled: str | None = None,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self,
        title: FormattedText,
        value: T,
        disabled: str | None = None,
        checked: bool | None = False,
        shortcut_key: str | bool | None = True,
        description: str | None = None,
    ) -> None: ...
