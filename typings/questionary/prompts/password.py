from typing import TYPE_CHECKING  # noqa: INP001

from questionary.constants import DEFAULT_QUESTION_PREFIX

if TYPE_CHECKING:
    from questionary import Style
    from questionary.question import Question


def password(
    message: str,
    default: str = "",
    validate: object = None,
    qmark: str = DEFAULT_QUESTION_PREFIX,
    style: Style | None = None,
    **kwargs: object,
) -> Question[str]: ...
