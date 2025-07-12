from collections.abc import Generator
from typing import Annotated, Any, ClassVar, Literal, Self, override

import rich
from keyring import get_password, set_password
from openai import BaseModel
from pwinput import pwinput
from pydantic import ConfigDict, PlainSerializer
from pydantic.json_schema import SkipJsonSchema
from requests_oauthlib import OAuth1Session
from rich.panel import Panel
from rich.prompt import Confirm


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
    def read_from_keyring(cls) -> Self:
        if json_data := get_password(cls.service_name, cls.username):
            return cls.model_validate_json(json_data)
        return cls()

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

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


class Post(FullyValidatedModel):
    class Block(FullyValidatedModel):
        type: str = "text"
        text: str = ""
        blocks: list[int] = []  # noqa: RUF012

    timestamp: SkipJsonSchema[int] = 0
    tags: Annotated[list[str], PlainSerializer(",".join)] = []  # noqa: RUF012
    state: SkipJsonSchema[Literal["published", "queued", "draft", "private", "unapproved"]] = "draft"

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

    def valid_text_post(self) -> bool:
        return bool(self.content) and all(block.type == "text" for block in self.content) and not (self.is_submission or self.trail or any(block.type == "ask" for block in self.layout))

    def get_content_text(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
