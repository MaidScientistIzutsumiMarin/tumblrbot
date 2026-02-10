from collections.abc import Callable, Sequence

from prompt_toolkit.styles import Style
from questionary.prompts.common import Choice
from questionary.question import Question

def checkbox[T](
    message: str,
    choices: Sequence[str | Choice[T] | dict[str, object]],
    default: str | None = None,
    validate: Callable[[list[str]], bool | str] = ...,
    qmark: str = ...,
    pointer: str | None = ...,
    style: Style | None = None,
    initial_choice: str | Choice[T] | dict[str, object] | None = None,
    use_arrow_keys: bool = True,
    use_jk_keys: bool = True,
    use_emacs_keys: bool = True,
    use_search_filter: str | bool | None = False,
    instruction: str | None = None,
    show_description: bool = True,
    **kwargs: object,
) -> Question[list[T]]: ...
