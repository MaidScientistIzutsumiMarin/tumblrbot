from collections.abc import Generator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, override

import rich
from openai.types import ChatModel
from pydantic import Field, PositiveFloat, PositiveInt, Secret, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource
from rich.prompt import Prompt
from tomlkit import comment, document, dumps  # pyright: ignore[reportUnknownVariableType]

if TYPE_CHECKING:
    from _typeshed import StrPath


class TOMLSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_return=True,
        validate_by_name=True,
    )

    @override
    @classmethod
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: PydanticBaseSettingsSource, **kwargs: PydanticBaseSettingsSource) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)

    @model_validator(mode="after")
    def write_to_file(self) -> Self:
        # Make sure to call this if updating values in nested models.
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
            dumps(toml_table),
            encoding="utf_8",
        )


class Config(TOMLSettings):
    model_config = SettingsConfigDict(
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
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        if not self.download_blog_identifiers:
            rich.print("Enter the [cyan]identifiers of your blogs[/] that data should be [bold purple]downloaded[/] from, separated by commas.")
            self.download_blog_identifiers = list(map(str.strip, Prompt.ask("[bold]Example: staff.tumblr.com,changes").split(",")))

        if not self.upload_blog_identifier:
            rich.print("Enter the [cyan]identifier of your blog[/] that drafts should be [bold purple]uploaded[/] to.")
            self.upload_blog_identifier = Prompt.ask("[bold]Examples: staff.tumblr.com or changes").strip()


class Tokens(TOMLSettings):
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

        if not self.openai_api_key.get_secret_value():
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not (self.tumblr_client_id.get_secret_value() and self.tumblr_client_secret.get_secret_value()):
            self.tumblr_client_id, self.tumblr_client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")
