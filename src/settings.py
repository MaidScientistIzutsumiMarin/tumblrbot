from pathlib import Path
from typing import Annotated, override

from openai import BaseModel
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt, Secret, StringConstraints
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, PyprojectTomlConfigSettingsSource

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Env(BaseSettings, env_file=".env"):
    tumblr_consumer_key: Secret[NonEmptyString]
    tumblr_consumer_secret: Secret[NonEmptyString]
    tumblr_oauth_token: Secret[NonEmptyString]
    tumblr_oauth_secret: Secret[NonEmptyString]

    openai_api_key: Secret[NonEmptyString]
    openai_model: Secret[NonEmptyString]

    blogname: NonEmptyString

    def __init__(self) -> None:
        super().__init__()


class Settings(BaseSettings, pyproject_toml_table_header=("tool", "tumblrbot")):
    class Generation(BaseModel):
        draft_count: NonNegativeInt
        tags_chance: NonNegativeFloat
        max_num_tags: PositiveInt

    class Training(BaseModel):
        output_file: Path
        expected_epochs: PositiveInt
        token_price: NonNegativeFloat

    generation: Generation
    training: Training

    system_message: NonEmptyString
    user_message: NonEmptyString
    model_name: NonEmptyString

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (PyprojectTomlConfigSettingsSource(settings_cls),)
