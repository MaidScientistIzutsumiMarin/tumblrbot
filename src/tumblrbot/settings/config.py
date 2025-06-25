from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, override

from openai.types import ChatModel
from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, TomlConfigSettingsSource
from tomlkit import comment, table
from tomlkit.items import Table

if TYPE_CHECKING:
    from _typeshed import StrPath


class AutoGenerateSettings(BaseSettings):
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        toml_files = self.model_config.get("toml_file")
        if isinstance(toml_files, (Path, str)):
            self.dump_toml(toml_files)
        elif isinstance(toml_files, Sequence):
            for toml_file in toml_files:
                self.dump_toml(toml_file)

    def dump_toml(self, toml_file: "StrPath") -> None:
        toml_path = Path(toml_file)
        if not (toml_path.exists() and toml_path.stat().st_size > 0):
            toml_path.write_text(self.get_toml_table().as_string())

    def get_toml_table(self) -> Table:
        toml_table = table()

        model_dump = self.model_dump(mode="json")
        for name, value in self.__class__.model_fields.items():
            if value.description:
                for line in value.description.split(". "):
                    toml_table.add(comment(f"{line.removesuffix('.')}."))

            if isinstance(value.default, AutoGenerateSettings):
                toml_table[name] = value.default.get_toml_table()
            else:
                toml_table[name] = model_dump[name]

        return toml_table


class Config(AutoGenerateSettings, cli_parse_args=True, cli_avoid_json=True, cli_kebab_case=True, toml_file="config.toml"):
    class Generation(AutoGenerateSettings):
        openai_model: str = Field("", description="Model to use for the OpenAI API. This is the model that will be used to generate draft text. You need to first generate the training data for this model.")
        blogname: str = Field(
            "",
            description='The name of the blog which generated drafts will be uploaded to that appears in the URL. This must be a blog associated with the same account as the configured Tumblr secret values. Examples: "staff" for https://staff.tumblr.com and "changes" for https://tumblr.com/changes or https://tumblr.com/@changes',
        )
        draft_count: NonNegativeInt = Field(150, description="The number of drafts to process. This will affect the number of tokens used with OpenAI. Setting to 0 will disable draft generation.")
        tags_chance: NonNegativeFloat = Field(0.1, description="The chance to generate tags for any given post. This will incur extra calls to OpenAI. Setting to 0 will disable tag generation. 0.1 is a 10% chance.")

    class Training(AutoGenerateSettings):
        blognames: list[str] = Field(
            [],
            description='The names of the blogs which post data will be downloaded from that appears in the URL. This must be a blog associated with the same account as the configured Tumblr secret values. Examples: ["staff", "changes"] for https://staff.tumblr.com and https://www.tumblr.com/changes or https://www.tumblr.com/@changes',
        )
        data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")
        output_file: Path = Field(Path("training.jsonl"), description="Where to output the training data that will be used to fine-tune the model.")
        target_epochs: PositiveInt = Field(3, description="The number of epochs fine-tuning will be run for.")
        max_output_tokens: PositiveInt = Field(32768, description="The max output tokens for the current model.")
        token_price: NonNegativeFloat = Field(1.50, description="The expected price in USD per million tokens during fine-tuning for the current model. Setting to 0 will treat fine-tuning as free.")

    user_message: str = Field("Write a comical Tumblr post.", description="The user message for the OpenAI API. This is the prompt that will be sent to the API to generate the text.")
    model_name: ChatModel = Field("gpt-4.1-nano", description="The name of the model that will be fine-tuned by the generated training data.")

    generation: Generation = Generation()  # pyright: ignore[reportCallIssue]
    training: Training = Training()  # pyright: ignore[reportCallIssue]

    @classmethod
    @override
    def settings_customise_sources(cls, settings_cls: type[BaseSettings], *args: object, **kwargs: object) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)


CONFIG = Config()  # pyright: ignore[reportCallIssue]
