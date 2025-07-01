from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from openai.types import ChatModel
from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource
from tomlkit import comment, dumps, table  # pyright: ignore[reportUnknownVariableType]
from tomlkit.items import Table

if TYPE_CHECKING:
    from _typeshed import StrPath


class TomlSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_return=True,
        validate_by_name=True,
    )

    def get_toml_table(self) -> Table:
        toml_table = table()

        dumped_model = self.model_dump(mode="json")
        for name, field in self.__class__.model_fields.items():
            if field.description:
                for line in field.description.split(". "):
                    toml_table.add(comment(f"{line.removesuffix('.')}."))

            value = getattr(self, name)
            toml_table[name] = value.get_toml_table() if isinstance(value, TomlSettings) else dumped_model[name]

        return toml_table


class AutoGenerateTomlSettings(TomlSettings):
    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: PydanticBaseSettingsSource, **kwargs: PydanticBaseSettingsSource) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)

    @override
    def model_post_init(self, context: object = None) -> None:
        super().model_post_init(context)

        # Make sure to call this if updating values in nested models.
        toml_files = self.model_config.get("toml_file")
        if isinstance(toml_files, (Path, str)):
            self.dump_toml(toml_files)
        elif isinstance(toml_files, Sequence):
            for toml_file in toml_files:
                self.dump_toml(toml_file)

    def dump_toml(self, toml_file: "StrPath") -> None:
        Path(toml_file).write_text(
            dumps(self.get_toml_table()),
            encoding="utf_8",
        )


class Config(AutoGenerateTomlSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        cli_avoid_json=True,
        cli_kebab_case=True,
        toml_file="config.toml",
    )

    class Generation(TomlSettings):
        fine_tuned_model: str = Field("", description="The name of the OpenAI model that was fine-tuned with your posts.")
        blog_name: str = Field(
            "",
            description='The name of the blog which generated drafts will be uploaded to that appears in the URL. This must be a blog associated with the same account as the configured Tumblr secret values. Examples: "staff" for https://staff.tumblr.com and "changes" for https://tumblr.com/changes or https://tumblr.com/@changes',
        )
        draft_count: PositiveInt = Field(150, description="The number of drafts to process. This will affect the number of tokens used with OpenAI")

    class Training(TomlSettings):
        blog_names: list[str] = Field(
            [],
            description='The names of the blogs which post data will be downloaded from that appears in the URL. This must be a blog associated with the same account as the configured Tumblr secret values. Examples: ["staff", "changes"] for https://staff.tumblr.com and https://www.tumblr.com/changes or https://www.tumblr.com/@changes',
        )
        data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")
        output_file: Path = Field(Path("training.jsonl"), description="Where to output the training data that will be used to fine-tune the model.")
        job_id: str = Field("", description="The fine-tuning job ID that will be polled on next run.")

        expected_epochs: PositiveInt = Field(3, description="The expected number of epochs fine-tuning will be run for. This will be updated during fine-tuning.")
        token_price: PositiveFloat = Field(1.50, description="The expected price in USD per million tokens during fine-tuning for the current model.")

    base_model: ChatModel = Field("gpt-4.1-nano-2025-04-14", description="The name of the model that will be fine-tuned by the generated training data.")

    developer_message: str = Field("You are a Tumblr post bot. Please generate a Tumblr post in accordance with the user's request.", description="The developer message used by the OpenAI API to generate drafts.")
    user_input: str = Field("Please write a comical Tumblr post.", description="The user input used by the OpenAI API to generate drafts.")
    tags_chance: float = Field(0.1, description="The chance to generate tags for any given post. This will incur extra calls to OpenAI.")

    generation: Generation = Generation()  # pyright: ignore[reportCallIssue]
    training: Training = Training()  # pyright: ignore[reportCallIssue]


class Tokens(AutoGenerateTomlSettings):
    model_config = SettingsConfigDict(toml_file="env.toml")

    class Tumblr(TomlSettings):
        client_id: str = ""
        client_secret: str = ""
        token: Any = {}

    openai_api_key: str = ""
    tumblr: Tumblr = Tumblr()
