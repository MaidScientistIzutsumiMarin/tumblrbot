import json
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self, override

import rich
import tomlkit
from keyring import get_password, set_password
from openai.types import ChatModel
from pydantic import Field, PositiveFloat, PositiveInt, Secret, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource
from requests_oauthlib import OAuth2Session
from rich.prompt import Confirm, Prompt
from tomlkit import comment, document

if TYPE_CHECKING:
    from _typeshed import StrPath


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_return=True,
        validate_by_name=True,
        cli_parse_args=True,
        cli_avoid_json=True,
        cli_kebab_case=True,
        toml_file="config.toml",
    )

    fine_tuned_model: str = Field("", description="The name of the OpenAI model that was fine-tuned with your posts.")
    upload_blog_identifier: str = Field(
        "",
        description="The identifier of the blog which generated drafts will be uploaded to. This must be a blog associated with the same account as the configured Tumblr secret tokens.",
    )
    draft_count: PositiveInt = Field(150, description="The number of drafts to process. This will affect the number of tokens used with OpenAI")
    tags_chance: float = Field(0.1, description="The chance to generate tags for any given post. This will incur extra calls to OpenAI.")

    download_blog_identifiers: list[str] = Field(
        [],
        description="The identifiers of the blogs which post data will be downloaded from. These must be blogs associated with the same account as the configured Tumblr secret tokens.",
    )
    data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")
    examples_file: Path = Field(Path("examples.jsonl"), description="Where to output the examples that will be used to fine-tune the model.")
    job_id: str = Field("", description="The fine-tuning job ID that will be polled on next run.")
    expected_epochs: PositiveInt = Field(3, description="The expected number of epochs fine-tuning will be run for. This will be updated during fine-tuning.")
    token_price: PositiveFloat = Field(1.50, description="The expected price in USD per million tokens during fine-tuning for the current model.")

    base_model: ChatModel = Field("gpt-4.1-nano-2025-04-14", description="The name of the model that will be fine-tuned by the generated training data.")
    developer_message: str = Field("You are a Tumblr post bot. Please generate a Tumblr post in accordance with the user's request.", description="The developer message used by the OpenAI API to generate drafts.")
    user_input: str = Field("Please write a comical Tumblr post.", description="The user input used by the OpenAI API to generate drafts.")

    @override
    @classmethod
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: PydanticBaseSettingsSource, **kwargs: PydanticBaseSettingsSource) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)

    @model_validator(mode="after")
    def write_to_file(self) -> Self:
        if not self.download_blog_identifiers:
            rich.print("Enter the [cyan]identifiers of your blogs[/] that data should be [bold purple]downloaded[/] from, separated by commas.")
            self.download_blog_identifiers = list(map(str.strip, Prompt.ask("[bold]Example: staff.tumblr.com,changes").split(",")))

        if not self.upload_blog_identifier:
            rich.print("Enter the [cyan]identifier of your blog[/] that drafts should be [bold purple]uploaded[/] to.")
            self.upload_blog_identifier = Prompt.ask("[bold]Examples: staff.tumblr.com or changes").strip()

        toml_files = self.model_config.get("toml_file")
        if isinstance(toml_files, (Path, str)):
            self.dump_toml(toml_files)
        elif isinstance(toml_files, Sequence):
            for toml_file in toml_files:
                self.dump_toml(toml_file)

        return self

    def dump_toml(self, toml_file: "StrPath") -> None:
        toml_table = document()

        dumped_model = self.model_dump(mode="json")
        for name, field in self.__class__.model_fields.items():
            if field.description:
                for line in field.description.split(". "):
                    toml_table.add(comment(f"{line.removesuffix('.')}."))

            value = getattr(self, name)
            toml_table[name] = value.get_secret_value() if isinstance(value, Secret) else dumped_model[name]

        Path(toml_file).write_text(
            tomlkit.dumps(toml_table),  # pyright: ignore[reportUnknownMemberType]
            encoding="utf_8",
        )


class Tokens(BaseSettings):
    service_name: ClassVar = "tumblrbot"
    model_config = SettingsConfigDict(toml_file="env.toml")

    openai_api_key: Secret[str] = Secret("")
    tumblr_client_id: Secret[str] = Secret("")
    tumblr_client_secret: Secret[str] = Secret("")
    tumblr_token: Secret[Any] = Secret({})

    @staticmethod
    def online_token_prompt(url: str, *tokens: str) -> Generator[Secret[str]]:
        formatted_tokens = [f"[cyan]{token}[/]" for token in tokens]
        formatted_token_string = " and ".join(formatted_tokens)

        rich.print(f"Retrieve your {formatted_token_string} from: {url}")
        for token in formatted_tokens:
            prompt = f"Enter your {token} [yellow](hidden)"
            yield Secret(Prompt.ask(prompt, password=True).strip())

        rich.print()

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        for name, _ in self:
            if value := get_password(self.service_name, name):
                setattr(self, name, Secret(json.loads(value)))

    @model_validator(mode="after")
    def write_to_keyring(self) -> Self:
        if not self.openai_api_key.get_secret_value() or Confirm.ask("Reset OpenAI API key?", default=False):
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not all(
            map(
                Secret[Any].get_secret_value,
                [
                    self.tumblr_client_id,
                    self.tumblr_client_secret,
                    self.tumblr_token,
                ],
            ),
        ) or Confirm.ask("Reset Tumblr API tokens?", default=False):
            self.tumblr_client_id, self.tumblr_client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

            oauth = OAuth2Session(
                self.tumblr_client_id.get_secret_value(),
                scope=["basic", "write", "offline_access"],
            )
            authorization_url, _ = oauth.authorization_url("https://tumblr.com/oauth2/authorize")  # pyright: ignore[reportUnknownMemberType]
            rich.print(f"Please go to {authorization_url} and authorize access.")
            self.tumblr_token = Secret(
                oauth.fetch_token(  # pyright: ignore[reportUnknownMemberType]
                    "https://api.tumblr.com/v2/oauth2/token",
                    authorization_response=Prompt.ask("Enter the full callback URL"),
                    client_secret=self.tumblr_client_secret.get_secret_value(),
                ),
            )

        for name, value in self:
            if isinstance(value, Secret):
                set_password(self.service_name, name, json.dumps(value.get_secret_value()))

        return self
