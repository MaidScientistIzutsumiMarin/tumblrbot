from typing import Literal, override

import rich
from keyring import get_password, set_password
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from rich.prompt import Prompt

from src.tumblrbot.common import yes_no_prompt
from src.tumblrbot.tumblr import generate_oauth_tokens


class KeyringSettingsSource(PydanticBaseSettingsSource):
    @override
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[str | None, str, Literal[False]]:
        return get_password("tumblrbot", field_name) or "", field_name, False

    @override
    def __call__(self) -> dict[str, object]:
        data: dict[str, object] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(field, field_name)
            data[field_key] = self.prepare_field_value(field_name, field, field_value, value_is_complex)

        return data


class Tokens(BaseSettings):
    tumblr_consumer_key: str
    tumblr_consumer_secret: str
    tumblr_oauth_token: str
    tumblr_oauth_secret: str
    openai_api_key: str

    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (KeyringSettingsSource(settings_cls),)

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        if "" in {self.tumblr_consumer_key, self.tumblr_consumer_secret, self.tumblr_oauth_token, self.tumblr_oauth_secret} or yes_no_prompt("Reset Tumblr tokens?", default=False):
            self.tumblr_consumer_key, self.tumblr_consumer_secret, self.tumblr_oauth_token, self.tumblr_oauth_secret = generate_oauth_tokens()

        if not self.openai_api_key or yes_no_prompt("Change OpenAI API key?", default=False):
            rich.print("Get an OpenAI API key here: https://platform.openai.com/account/api-keys")
            self.openai_api_key = Prompt.ask("Enter the key").strip()

        self.save_tokens()

    def save_tokens(self) -> None:
        for name, value in self.model_dump().items():
            set_password("tumblrbot", name, value)


TOKENS = Tokens()  # pyright: ignore[reportCallIssue]
