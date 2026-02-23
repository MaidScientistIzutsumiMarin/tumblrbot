from collections.abc import Sequence

from prompt_toolkit.styles import Style
from questionary.prompts.common import Choice
from questionary.question import Question

def select[T](
    message: str,
    choices: Sequence[str | Choice[T] | dict[str, object]],
    default: str | Choice[T] | dict[str, object] | None = None,
    qmark: str = ...,
    pointer: str | None = ...,
    style: Style | None = None,
    use_shortcuts: bool = False,
    use_arrow_keys: bool = True,
    use_indicator: bool = False,
    use_jk_keys: bool = True,
    use_emacs_keys: bool = True,
    use_search_filter: bool = False,
    show_selected: bool = False,
    show_description: bool = True,
    instruction: str | None = None,
    **kwargs: object,
) -> Question[T]: ...
