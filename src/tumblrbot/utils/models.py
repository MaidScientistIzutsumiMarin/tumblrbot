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
from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PlainSerializer, PositiveFloat, PositiveInt, model_validator
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
    def write(self) -> Self: ...


class Config(FileSyncSettings):
    toml_file: ClassVar = Path("config.toml")

    tokens_profile: str = Field("tokens", description="The name under which API keys are stored and retrieved.")

    # Downloading Posts & Writing Examples
    download_blog_identifiers: list[str] = Field([], description="The identifiers of the blogs which post data will be downloaded from.")
    data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")

    # Writing Examples
    post_limit: NonNegativeInt = Field(0, description="The number of the most recent posts from each blog that should be included in the training data.")
    max_moderation_batch_size: PositiveInt = Field(100, description="The number of posts, at most, to submit to the OpenAI moderation API. This is also capped by the API.")
    custom_prompts_file: Path = Field(Path("custom_prompts.jsonl"), description="Where to read in custom prompts from.")
    filtered_words: list[str] = Field([], description="A case-insensitive list of disallowed words used to filter out training data. Regular expressions are allowed, but must be escaped.")

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
    tags_chance: NonNegativeFloat = Field(0.1, description="The chance to generate tags for any given post. This will use more OpenAI tokens.")
    tags_developer_message: str = Field("You will be provided with a block of text, and your task is to extract a very short list of the most important subjects from it.", description="The developer message used to generate tags.")
    reblog_blog_identifiers: list[str] = Field([], description="The identifiers of blogs that can be reblogged from when generating drafts.")
    reblog_chance: NonNegativeFloat = Field(0.1, description="The chance to generate a reblog of a random post. This will use more OpenAI tokens.")
    reblog_user_message: str = Field("Please write a comical Tumblr post in response to the following post:\n\n{}", description="The format string for the user message used to reblog posts.")

    @classmethod
    @override
    def read(cls) -> dict[str, object] | None:
        return tomllib.loads(cls.toml_file.read_text("utf_8")) if cls.toml_file.exists() else None

    @model_validator(mode="after")
    @override
    def write(self) -> Self:
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

        self.toml_file.write_text(tomlkit.dumps(toml_table), encoding="utf_8")

        return self


class Tokens(FileSyncSettings):
    class Tumblr(FullyValidatedModel):
        client_key: str = ""
        client_secret: str = ""
        resource_owner_key: str = ""
        resource_owner_secret: str = ""

    service_name: ClassVar = "tumblrbot"
    username: ClassVar = Config.load().tokens_profile  # This is gross but we don't really know a better way to do this...

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
    def write(self) -> Self:
        # Check if any tokens are missing or if the user wants to reset them, then set tokens if necessary.
        if not self.openai_api_key or Confirm.ask("Reset OpenAI API key?", default=False):
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not all(self.tumblr.model_dump().values()) or Confirm.ask("Reset Tumblr API tokens?", default=False):
            self.tumblr.client_key, self.tumblr.client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

            # This is the whole OAuth 1.0 process.
            # https://requests-oauthlib.readthedocs.io/en/latest/examples/tumblr.html
            # We tried setting up OAuth 2.0, but the token refresh process is far too unreliable for this sort of program.
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

        # Regardless of whether any values were changed, we may as well write to the keyring.
        # Any unchanged values will be set to the value they already were, since this is run after reading from the keyring.
        set_password(self.service_name, self.username, self.model_dump_json())

        return self


class Blog(FullyValidatedModel):
    name: str = ""
    posts: int = 0
    uuid: str = ""


class ResponseModel(FullyValidatedModel):
    class Response(FullyValidatedModel):
        blog: Blog = Blog()
        posts: list[Any] = []

    response: Response


class Post(FullyValidatedModel):
    class Block(FullyValidatedModel):
        type: str = ""
        text: str = ""
        blocks: list[int] = []

    blog: SkipJsonSchema[Blog] = Blog()
    id: SkipJsonSchema[int] = 0
    parent_tumblelog_uuid: SkipJsonSchema[str] = ""
    parent_post_id: SkipJsonSchema[int] = 0
    reblog_key: SkipJsonSchema[str] = ""

    timestamp: SkipJsonSchema[int] = 0
    tags: Annotated[list[str], PlainSerializer(",".join)] = []
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "published"

    content: SkipJsonSchema[list[Block]] = []
    layout: SkipJsonSchema[list[Block]] = []
    trail: SkipJsonSchema[list[Self]] = []

    is_submission: SkipJsonSchema[bool] = False

    def __rich__(self) -> Panel:
        return Panel(
            str(self),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    def __str__(self) -> str:
        # This function is really only relevant when a post is already valid, so we don't have to check the block types.
        # If it is called on an invalid post, it would also work, but might give strange data.
        return "\n\n".join(block.text for block in self.content)

    def valid_text_post(self) -> bool:
        # Checks if this post:
        # - has any content blocks (some glitched empty posts have no content)
        # - only has content blocks of type 'text' (this excludes photo/video/poll/etc posts)
        # - is not a submitted post
        # - has no ask blocks in the content
        return bool(self.content) and all(block.type == "text" for block in self.content) and not (self.is_submission or any(block.type == "ask" for block in self.layout))


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
