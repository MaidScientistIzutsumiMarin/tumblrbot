import tomllib
from abc import abstractmethod
from collections.abc import Generator
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, Self, override

import rich
import tomlkit
from keyring import get_password, set_password
from openai.types import ChatModel
from pwinput import pwinput
from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PlainSerializer, PositiveFloat, PositiveInt, model_validator
from pydantic.json_schema import SkipJsonSchema
from requests_oauthlib import OAuth1Session
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from tomlkit import comment, document


class FullyValidatedModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_default=True,
        validate_return=True,
        validate_by_name=True,
    )


class FileSyncSettings(FullyValidatedModel):
    @classmethod
    @abstractmethod
    def read(cls) -> Self | dict[str, object] | str | None: ...

    @classmethod
    def load(cls) -> Self:
        data = cls.read() or {}
        return cls.model_validate_json(data) if isinstance(data, str) else cls.model_validate(data)

    @model_validator(mode="after")
    @abstractmethod
    def save(self) -> Self: ...


class Config(FileSyncSettings):
    toml_file: ClassVar = Path("config.toml")

    # Downloading Posts & Writing Examples
    download_blog_identifiers: list[str] = Field([], description="The identifiers of the blogs which post data will be downloaded from. These must be blogs associated with the same account as the configured Tumblr secret tokens.")
    data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")

    # Writing Examples
    max_moderation_batch_size: PositiveInt = Field(100, description="How many posts, at most, to submit to the OpenAI moderation API. This is also capped by the API.")
    custom_prompts_file: Path = Field(Path("custom_prompts.jsonl"), description="Where to read in custom prompts from.")

    # Writing Examples & Fine-Tuning
    examples_file: Path = Field(Path("examples.jsonl"), description="Where to output the examples that will be used to fine-tune the model.")

    # Writing Examples & Generating
    developer_message: str = Field("You are a Tumblr post bot. Please generate a Tumblr post in accordance with the user's request.", description="The developer message used by the OpenAI API to generate drafts.")
    user_message: str = Field("Please write a comical Tumblr post.", description="The user input used by the OpenAI API to generate drafts.")

    # Fine-Tuning
    expected_epochs: PositiveInt = Field(3, description="The expected number of epochs fine-tuning will be run for. This will be updated during fine-tuning.")
    token_price: PositiveFloat = Field(3, description="The expected price in USD per million tokens during fine-tuning for the current model.")
    job_id: str = Field("", description="The fine-tuning job ID that will be polled on next run.")

    # Fine-Tuning & Generating
    base_model: ChatModel = Field("gpt-4o-mini-2024-07-18", description="The name of the model that will be fine-tuned by the generated training data.")
    fine_tuned_model: str = Field("", description="The name of the OpenAI model that was fine-tuned with your posts.")

    # Generating
    upload_blog_identifier: str = Field("", description="The identifier of the blog which generated drafts will be uploaded to. This must be a blog associated with the same account as the configured Tumblr secret tokens.")
    draft_count: PositiveInt = Field(150, description="The number of drafts to process. This will affect the number of tokens used with OpenAI")
    tags_chance: NonNegativeFloat = Field(0.1, description="The chance to generate tags for any given post. This will incur extra calls to OpenAI.")
    tags_developer_message: str = Field("You will be provided with a block of text, and your task is to extract a very short list of the most important subjects from it.", description="The developer message used to generate tags.")

    @classmethod
    @override
    def read(cls) -> dict[str, object] | None:
        return tomllib.loads(cls.toml_file.read_text()) if cls.toml_file.exists() else None

    @model_validator(mode="after")
    @override
    def save(self) -> Self:
        if not self.download_blog_identifiers:
            rich.print("Enter the [cyan]identifiers of your blogs[/] that data should be [bold purple]downloaded[/] from, separated by commas.")
            self.download_blog_identifiers = list(map(str.strip, Prompt.ask("[bold][Example] [dim]staff.tumblr.com,changes").split(",")))

        if not self.upload_blog_identifier:
            rich.print("Enter the [cyan]identifier of your blog[/] that drafts should be [bold purple]uploaded[/] to.")
            self.upload_blog_identifier = Prompt.ask("[bold][Example] [dim]staff.tumblr.com or changes").strip()

        toml_table = document()

        for (name, field), value in zip(self.__class__.model_fields.items(), self.model_dump(mode="json").values(), strict=True):
            if field.description is not None:
                for line in field.description.split(". "):
                    toml_table.add(comment(f"{line.removesuffix('.')}."))

            toml_table[name] = value

        Path(self.toml_file).write_text(tomlkit.dumps(toml_table), encoding="utf_8")

        return self


class Tokens(FileSyncSettings):
    class Tumblr(FullyValidatedModel):
        client_key: str = ""
        client_secret: str = ""
        resource_owner_key: str = ""
        resource_owner_secret: str = ""

    service_name: ClassVar = "tumblrbot"
    username: ClassVar = "tokens"

    openai_api_key: str = ""
    tumblr: Tumblr = Tumblr()

    @staticmethod
    def get_oauth_tokens(token: dict[str, str]) -> tuple[str, str]:
        return token["oauth_token"], token["oauth_token_secret"]

    @staticmethod
    def online_token_prompt(url: str, *tokens: str) -> Generator[str]:
        formatted_token_string = " and ".join(f"[cyan]{token}[/]" for token in tokens)

        rich.print(f"Retrieve your {formatted_token_string} from: {url}")
        for token in tokens:
            yield pwinput(f"Enter your {token} (masked): ").strip()

        rich.print()

    @classmethod
    @override
    def read(cls) -> str | None:
        return get_password(cls.service_name, cls.username)

    @model_validator(mode="after")
    @override
    def save(self) -> Self:
        if not self.openai_api_key or Confirm.ask("Reset OpenAI API key?", default=False):
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not all(self.tumblr.model_dump().values()) or Confirm.ask("Reset Tumblr API tokens?", default=False):
            self.tumblr.client_key, self.tumblr.client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

            with OAuth1Session(
                self.tumblr.client_key,
                self.tumblr.client_secret,
            ) as oauth_session:
                fetch_response = oauth_session.fetch_request_token("http://tumblr.com/oauth/request_token")
                full_authorize_url = oauth_session.authorization_url("http://tumblr.com/oauth/authorize")
                (redirect_response,) = self.online_token_prompt(full_authorize_url, "full redirect URL")
                oauth_response = oauth_session.parse_authorization_response(redirect_response)

            with OAuth1Session(
                self.tumblr.client_key,
                self.tumblr.client_secret,
                *self.get_oauth_tokens(fetch_response),
                verifier=oauth_response["oauth_verifier"],
            ) as oauth_session:
                oauth_tokens = oauth_session.fetch_access_token("http://tumblr.com/oauth/access_token")

            self.tumblr.resource_owner_key, self.tumblr.resource_owner_secret = self.get_oauth_tokens(oauth_tokens)

        set_password(self.service_name, self.username, self.model_dump_json())

        return self


class Post(FullyValidatedModel):
    class Block(FullyValidatedModel):
        type: str = "text"
        text: str = ""
        blocks: list[int] = []

    timestamp: SkipJsonSchema[int] = 0
    tags: Annotated[list[str], PlainSerializer(",".join)] = []
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "draft"

    content: SkipJsonSchema[list[Block]] = []
    layout: SkipJsonSchema[list[Block]] = []
    trail: SkipJsonSchema[list[Any]] = []

    is_submission: SkipJsonSchema[bool] = False

    def __rich__(self) -> Panel:
        return Panel(
            self.get_content_text(),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    def valid_text_post(self) -> bool:
        return bool(self.content) and all(block.type == "text" for block in self.content) and not (self.is_submission or self.trail or any(block.type == "ask" for block in self.layout))

    def get_content_text(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
