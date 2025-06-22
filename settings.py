from functools import cache
from pathlib import Path
from typing import Annotated, override

from openai import BaseModel
from openai.types import ChatModel
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt, Secret, StringConstraints
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource

# Having values validated as non-empty should make it easier for users to diagnose configuration issues.
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Env(BaseSettings, env_file=".env"):
    tumblr_consumer_key: Secret[NonEmptyString]
    tumblr_consumer_secret: Secret[NonEmptyString]
    tumblr_oauth_token: Secret[NonEmptyString]
    tumblr_oauth_secret: Secret[NonEmptyString]

    openai_api_key: Secret[NonEmptyString]
    openai_model: Secret[NonEmptyString]

    blogname: NonEmptyString


class Settings(BaseSettings, toml_file="config.toml"):
    class Generation(BaseModel):
        draft_count: NonNegativeInt
        tags_chance: NonNegativeFloat
        max_num_tags: PositiveInt

    class Training(BaseModel):
        data_directory: Path
        output_file: Path
        max_output_tokens: PositiveInt
        token_price: NonNegativeFloat

    generation: Generation
    training: Training

    system_message: NonEmptyString
    user_message: NonEmptyString
    model_name: ChatModel

    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)


SETTINGS = Settings()  # pyright: ignore[reportCallIssue]


@cache
def get_env() -> Env:
    return Env()  # pyright: ignore[reportCallIssue]
