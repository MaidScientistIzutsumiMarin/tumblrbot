from typing import TYPE_CHECKING  # noqa: INP001

from questionary.constants import DEFAULT_QUESTION_PREFIX

if TYPE_CHECKING:
    from prompt_toolkit.lexers import Lexer
    from prompt_toolkit.styles import Style
    from questionary.question import Question


def text(  # noqa: PLR0913
    message: str,
    default: str = "",
    validate: object = None,
    qmark: str = DEFAULT_QUESTION_PREFIX,
    style: Style | None = None,
    *,
    multiline: bool = False,
    instruction: str | None = None,
    lexer: Lexer | None = None,
    **kwargs: object,
) -> Question[str]: ...
