from pathlib import Path
from typing import Annotated, override

from openai import BaseModel
from openai.types import ChatModel
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt, Secret, StringConstraints
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource

# Having values validated as non-empty should make it easier for users to diagnose configuration issues.
NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TOMLSettings(BaseSettings):
    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)


class Env(TOMLSettings, toml_file=".env.toml"):
    tumblr_consumer_key: NonEmptyString
    tumblr_consumer_secret: Secret[NonEmptyString]
    tumblr_oauth_token: NonEmptyString
    tumblr_oauth_secret: Secret[NonEmptyString]

    openai_api_key: Secret[NonEmptyString]
    openai_model: NonEmptyString


class Settings(TOMLSettings, toml_file="config.toml", cli_parse_args=True, cli_kebab_case=True, cli_avoid_json=True):
    class Generation(BaseModel):
        blogname: NonEmptyString
        draft_count: NonNegativeInt
        tags_chance: NonNegativeFloat

    class Training(BaseModel):
        blognames: list[NonEmptyString]
        data_directory: Path
        output_file: Path
        target_epochs: PositiveInt
        max_output_tokens: PositiveInt
        token_price: NonNegativeFloat

    generation: Generation
    training: Training

    user_message: str
    model_name: ChatModel


ENV = Env()  # pyright: ignore[reportCallIssue]
SETTINGS = Settings()  # pyright: ignore[reportCallIssue]
