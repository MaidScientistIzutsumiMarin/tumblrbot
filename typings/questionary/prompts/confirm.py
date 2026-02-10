from typing import TYPE_CHECKING  # noqa: INP001

from questionary.constants import DEFAULT_QUESTION_PREFIX

if TYPE_CHECKING:
    from prompt_toolkit.styles import Style
    from questionary.question import Question


def confirm(  # noqa: PLR0913
    message: str,
    *,
    default: bool = True,
    qmark: str = DEFAULT_QUESTION_PREFIX,
    style: Style | None = None,
    auto_enter: bool = True,
    instruction: str | None = None,
    **kwargs: object,
) -> Question[bool]: ...
