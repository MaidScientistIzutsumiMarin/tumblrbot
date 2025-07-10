from collections.abc import Generator
from typing import Annotated, Any, ClassVar, Literal, Self, override

from niquests import Session
import rich
from keyring import get_password, set_password
from openai import BaseModel
from pwinput import pwinput
from pydantic import ConfigDict, PlainSerializer, SecretStr
from pydantic.json_schema import SkipJsonSchema
from requests_oauthlib import OAuth1Session
from rich.panel import Panel
from rich.prompt import Confirm

type SerializableSecretStr = Annotated[
    SecretStr,
    PlainSerializer(
        SecretStr.get_secret_value,
        when_used="json-unless-none",
    ),
]


class FullyValidatedModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_default=True,
        validate_return=True,
        validate_by_name=True,
    )


class Tokens(FullyValidatedModel):
    class Tumblr(FullyValidatedModel):
        client_key: SerializableSecretStr = SecretStr("")
        client_secret: SerializableSecretStr = SecretStr("")
        resource_owner_key: SerializableSecretStr = SecretStr("")
        resource_owner_secret: SerializableSecretStr = SecretStr("")

    service_name: ClassVar = "tumblrbot"
    username: ClassVar = "tokens"

    openai_api_key: SerializableSecretStr = SecretStr("")
    tumblr: Tumblr = Tumblr()

    @staticmethod
    def online_token_prompt(url: str, *tokens: str) -> Generator[SecretStr]:
        formatted_token_string = " and ".join(f"[cyan]{token}[/]" for token in tokens)

        rich.print(f"Retrieve your {formatted_token_string} from: {url}")
        for token in tokens:
            yield SecretStr(pwinput(f"Enter your {token} (masked): ").strip())

        rich.print()

    @classmethod
    def read_from_keyring(cls) -> Self:
        if json_data := get_password(cls.service_name, cls.username):
            return cls.model_validate_json(json_data)
        return cls()

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        if not self.openai_api_key.get_secret_value() or Confirm.ask("Reset OpenAI API key?", default=False):
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not all(self.tumblr.model_dump(mode="json").values()) or Confirm.ask("Reset Tumblr API tokens?", default=False):
            self.tumblr.client_key, self.tumblr.client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

            OAuth1Session.__bases__ = (Session,)

            with OAuth1Session(
                self.tumblr.client_key.get_secret_value(),
                self.tumblr.client_secret.get_secret_value(),
            ) as oauth_session:
                fetch_response = oauth_session.fetch_request_token("http://tumblr.com/oauth/request_token")
                full_authorize_url = oauth_session.authorization_url("http://tumblr.com/oauth/authorize")
                (redirect_response,) = self.online_token_prompt(full_authorize_url, "full redirect URL")
                oauth_response = oauth_session.parse_authorization_response(redirect_response.get_secret_value())

            with OAuth1Session(
                self.tumblr.client_key.get_secret_value(),
                self.tumblr.client_secret.get_secret_value(),
                fetch_response["oauth_token"],
                fetch_response["oauth_token_secret"],
                verifier=oauth_response["oauth_verifier"],
            ) as oauth_session:
                oauth_tokens = oauth_session.fetch_access_token("http://tumblr.com/oauth/access_token")

            self.tumblr.resource_owner_key = oauth_tokens["oauth_token"]
            self.tumblr.resource_owner_secret = oauth_tokens["oauth_token_secret"]

        set_password(self.service_name, self.username, self.model_dump_json())


class Post(FullyValidatedModel):
    class Block(FullyValidatedModel):
        type: str = ""
        text: str = ""
        blocks: list[int] = []  # noqa: RUF012

    timestamp: SkipJsonSchema[int] = 0
    tags: Annotated[list[str], PlainSerializer(",".join)] = []  # noqa: RUF012
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "published"

    content: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    layout: SkipJsonSchema[list[Block]] = []  # noqa: RUF012
    trail: SkipJsonSchema[list[Any]] = []  # noqa: RUF012

    is_submission: SkipJsonSchema[bool] = False

    def __rich__(self) -> Panel:
        return Panel(
            self.get_content_text(),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    def only_text_blocks(self) -> bool:
        return all(block.type == "text" for block in self.content) and not any(block.type == "ask" for block in self.layout)

    def get_content_text(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
