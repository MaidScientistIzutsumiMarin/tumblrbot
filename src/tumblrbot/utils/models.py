from getpass import getpass
from pathlib import Path
from tomllib import loads
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self, override

from openai.types import ResponsesModel  # noqa: TC002
from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt, PlainSerializer, PositiveFloat, PositiveInt, model_validator
from pydantic.json_schema import SkipJsonSchema  # noqa: TC002
from requests_oauthlib import OAuth1Session
from rich import print as rich_print
from rich.panel import Panel
from rich.prompt import Prompt
from tomlkit import comment, document, dumps  # pyright: ignore[reportUnknownVariableType]

if TYPE_CHECKING:
    from collections.abc import Generator


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
    def get_toml_file(cls) -> Path:
        return Path(f"{cls.__name__.lower()}.toml")

    @classmethod
    def load(cls) -> Self:
        toml_file = cls.get_toml_file()
        data = loads(toml_file.read_text("utf_8")) if toml_file.exists() else {}
        return cls.model_validate(data)

    @model_validator(mode="after")
    def dump(self) -> Self:
        toml_table = document()

        for (name, field), value in zip(self.__class__.model_fields.items(), self.model_dump(mode="json").values(), strict=True):
            if field.description is not None:
                for line in field.description.split(". "):
                    toml_table.add(comment(f"{line.removesuffix('.')}."))

            toml_table[name] = value

        self.get_toml_file().write_text(dumps(toml_table), encoding="utf_8")

        return self


class Config(FileSyncSettings):
    # Downloading Posts & Writing Examples
    download_blog_identifiers: list[str] = Field([], description="The identifiers of the blogs which post data will be downloaded from.")
    data_directory: Path = Field(Path("data"), description="Where to store downloaded post data.")

    # Writing Examples
    post_limit: NonNegativeInt = Field(0, description="The number of the most recent posts from each blog that should be included in the training data.")
    moderation_batch_size: PositiveInt = Field(25, description="The number of posts at a time to submit to the OpenAI moderation API.")
    custom_prompts_file: Path = Field(Path("custom_prompts.jsonl"), description="Where to read in custom prompts from.")
    filtered_words: list[str] = Field([], description="A case-insensitive list of disallowed words used to filter out training data. Regular expressions are allowed, but must be escaped.")

    # Writing Examples & Fine-Tuning
    training_data_file: Path = Field(Path("training_data.jsonl"), description="Where to output the training data that will be used to fine-tune the model.")

    # Writing Examples & Generating
    developer_message: str = Field("You are a Tumblr post bot. Please generate a Tumblr post in accordance with the user's request.", description="The developer message used by the OpenAI API to generate drafts.")
    user_message: str = Field("Please write a comical Tumblr post.", description="The user input used by the OpenAI API to generate drafts.")

    # Fine-Tuning
    expected_epochs: PositiveInt = Field(3, description="The expected number of epochs fine-tuning will be run for. This will be updated during fine-tuning.")
    token_price: PositiveFloat = Field(3, description="The expected price in USD per million tokens during fine-tuning for the current model.")
    job_id: str = Field("", description="The fine-tuning job ID that will be polled on next run.")

    # Fine-Tuning & Generating
    base_model: ResponsesModel = Field("gpt-4o-mini-2024-07-18", description="The name of the model that will be fine-tuned by the generated training data.")
    fine_tuned_model: str = Field("", description="The name of the OpenAI model that was fine-tuned with your posts.")

    # Generating
    upload_blog_identifier: str = Field("", description="The identifier of the blog which generated drafts will be uploaded to. This must be a blog associated with the same account as the configured Tumblr secret tokens.")
    draft_count: PositiveInt = Field(100, description="The number of drafts to process. This will affect the number of tokens used with OpenAI")
    tags_chance: NonNegativeFloat = Field(0.1, description="The chance to generate tags for any given post. This will use more OpenAI tokens.")
    tags_developer_message: str = Field("You will be provided with a block of text, and your task is to extract a very short list of the most important subjects from it.", description="The developer message used to generate tags.")
    reblog_blog_identifiers: list[str] = Field([], description="The identifiers of blogs that can be reblogged from when generating drafts.")
    reblog_chance: NonNegativeFloat = Field(0.1, description="The chance to generate a reblog of a random post. This will use more OpenAI tokens.")
    reblog_user_message: str = Field("Please write a comical Tumblr post in response to the following post:\n\n{}", description="The format string for the user message used to reblog posts.")

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        if not self.download_blog_identifiers:
            rich_print("Enter the [cyan]identifiers of your blogs[/] that data should be [bold purple]downloaded[/] from, separated by commas.")
            self.download_blog_identifiers = list(map(str.strip, Prompt.ask("[bold][Example] [dim]staff.tumblr.com,changes").split(",")))

        if not self.upload_blog_identifier:
            rich_print("Enter the [cyan]identifier of your blog[/] that drafts should be [bold purple]uploaded[/] to.")
            self.upload_blog_identifier = Prompt.ask("[bold][Example] [dim]staff.tumblr.com or changes").strip()


class Tokens(FileSyncSettings):
    class Tumblr(FullyValidatedModel):
        client_key: str = ""
        client_secret: str = ""
        resource_owner_key: str = ""
        resource_owner_secret: str = ""

    openai_api_key: str = ""
    tumblr: Tumblr = Tumblr()

    @staticmethod
    def online_token_prompt(url: str, *tokens: str) -> Generator[str]:
        formatted_token_string = " and ".join(f"[cyan]{token}[/]" for token in tokens)

        rich_print(f"Retrieve your {formatted_token_string} from: {url}")
        for token in tokens:
            yield getpass(f"Enter your {token} (masked): ", echo_char="*").strip()

        rich_print()

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        if not self.openai_api_key:
            self.set_openai_token()
        if not all(self.tumblr.model_dump().values()):
            self.set_tumblr_tokens()

    def set_openai_token(self) -> None:
        (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

    def set_tumblr_tokens(self) -> None:
        self.tumblr.client_key, self.tumblr.client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

        # This is the whole OAuth 1.0 process.
        # https://requests-oauthlib.readthedocs.io/en/latest/examples/tumblr.html
        # We tried setting up OAuth 2.0, but the token refresh process is far too unreliable for this sort of program.
        with OAuth1Session(**self.tumblr.model_dump()) as session:
            session.fetch_request_token("http://tumblr.com/oauth/request_token")  # pyright: ignore[reportUnknownMemberType]

            rich_print("Open the link below in your browser, and authorize this application.\nAfter authorizing, copy and paste the URL of the page you are redirected to below.")
            authorization_url = session.authorization_url("http://tumblr.com/oauth/authorize")  # pyright: ignore[reportUnknownMemberType]
            (authorization_response,) = self.online_token_prompt(authorization_url, "full redirect URL")
            session.parse_authorization_response(authorization_response)

            access_token = session.fetch_access_token("http://tumblr.com/oauth/access_token")  # pyright: ignore[reportUnknownMemberType]

        self.tumblr.resource_owner_key = access_token["oauth_token"]
        self.tumblr.resource_owner_secret = access_token["oauth_token_secret"]


class Blog(FullyValidatedModel):
    name: str = ""
    posts: int = 0
    uuid: str = ""


class ResponseModel(FullyValidatedModel):
    class Response(FullyValidatedModel):
        blog: Blog = Blog()
        posts: list[Any] = []

    response: Response


class Block(FullyValidatedModel):
    type: str = "text"
    text: str = ""
    blocks: list[int] = []


class Post(FullyValidatedModel):
    blog: Blog = Blog()
    id: int = 0
    parent_tumblelog_uuid: str = ""
    parent_post_id: int = 0
    reblog_key: str = ""

    timestamp: int = 0
    tags: Annotated[list[str], PlainSerializer(",".join)] = []
    state: Literal["published", "queued", "draft", "private", "unapproved"] = "draft"

    content: list[Block] = []
    layout: list[Block] = []
    trail: list[Self] = []

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


class Message(FullyValidatedModel):
    role: Literal["developer", "user", "assistant"]
    content: str


class Example(FullyValidatedModel):
    messages: list[Message]

    def get_assistant_message(self) -> str:
        for message in self.messages:
            if message.role == "assistant":
                return message.content
        msg = "Assistant message not found!"
        raise ValueError(msg)
