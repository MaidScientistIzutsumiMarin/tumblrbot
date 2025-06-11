from pathlib import Path
from typing import ClassVar, override

from openai import BaseModel
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, PyprojectTomlConfigSettingsSource


class Settings(BaseSettings, pyproject_toml_table_header=("tool", "tumblrbot")):
    class Env(BaseSettings, env_file=".env"):
        tumblr_consumer_key: str
        tumblr_consumer_secret: str
        tumblr_oauth_token: str
        tumblr_oauth_secret: str

        openai_api_key: str
        openai_model: str

        blogname: str

        def __init__(self) -> None:
            super().__init__()

    class Generation(BaseModel):
        draft_count: int = Field(ge=0)
        tags_chance: float = Field(ge=0)
        max_num_tags: int = Field(ge=1)

    class Training(BaseModel):
        output_file: Path
        expected_epochs: int = Field(gt=0)
        token_price: float = Field(ge=0)

    env: ClassVar = Env()
    generation: Generation
    training: Training

    system_message: str
    user_message: str
    model_name: str

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (PyprojectTomlConfigSettingsSource(settings_cls),)
