from collections.abc import Generator
from typing import Annotated, Any, ClassVar, Literal, override

import rich
from keyring import get_password, set_password
from openai import BaseModel
from pydantic import ConfigDict, PlainSerializer, SecretStr
from pydantic.json_schema import SkipJsonSchema
from requests_oauthlib import OAuth1Session
from rich.panel import Panel
from rich.prompt import Confirm, Prompt


class FullyValidatedModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_default=True,
        validate_return=True,
        validate_by_name=True,
    )


class Tokens(FullyValidatedModel):
    service_name: ClassVar = "tumblrbot"

    openai_api_key: SecretStr = SecretStr("")
    tumblr_client_key: SecretStr = SecretStr("")
    tumblr_client_secret: SecretStr = SecretStr("")
    tumblr_resource_owner_key: SecretStr = SecretStr("")
    tumblr_resource_owner_secret: SecretStr = SecretStr("")

    @staticmethod
    def online_token_prompt(url: str, *tokens: str) -> Generator[SecretStr]:
        formatted_tokens = [f"[cyan]{token}[/]" for token in tokens]
        formatted_token_string = " and ".join(formatted_tokens)

        rich.print(f"Retrieve your {formatted_token_string} from: {url}")
        for token in formatted_tokens:
            prompt = f"Enter your {token} [yellow](hidden)"
            yield SecretStr(Prompt.ask(prompt, password=True).strip())

        rich.print()

    @override
    def model_post_init(self, context: object) -> None:
        super().model_post_init(context)

        for name, _ in self:
            if value := get_password(self.service_name, name):
                setattr(self, name, value)

        if not self.openai_api_key.get_secret_value() or Confirm.ask("Reset OpenAI API key?", default=False):
            (self.openai_api_key,) = self.online_token_prompt("https://platform.openai.com/api-keys", "API key")

        if not all(self.get_tumblr_tokens()) or Confirm.ask("Reset Tumblr API tokens?", default=False):
            self.tumblr_client_key, self.tumblr_client_secret = self.online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

            oauth_session = OAuth1Session(*self.get_tumblr_tokens()[:2])
            fetch_response = oauth_session.fetch_request_token("http://tumblr.com/oauth/request_token")  # pyright: ignore[reportUnknownMemberType]
            full_authorize_url = oauth_session.authorization_url("http://tumblr.com/oauth/authorize")  # pyright: ignore[reportUnknownMemberType]
            (redirect_response,) = self.online_token_prompt(full_authorize_url, "full redirect URL")
            oauth_response = oauth_session.parse_authorization_response(redirect_response.get_secret_value())
            oauth_session = OAuth1Session(
                *self.get_tumblr_tokens()[:2],
                fetch_response["oauth_token"],
                fetch_response["oauth_token_secret"],
                verifier=oauth_response["oauth_verifier"],
            )
            oauth_tokens = oauth_session.fetch_access_token("http://tumblr.com/oauth/access_token")  # pyright: ignore[reportUnknownMemberType]
            self.tumblr_resource_owner_key = oauth_tokens["oauth_token"]
            self.tumblr_resource_owner_secret = oauth_tokens["oauth_token_secret"]

        for name, value in self:
            if isinstance(value, SecretStr):
                set_password(self.service_name, name, value.get_secret_value())

    def get_tumblr_tokens(self) -> tuple[str, str, str, str]:
        return (
            self.tumblr_client_key.get_secret_value(),
            self.tumblr_client_secret.get_secret_value(),
            self.tumblr_resource_owner_key.get_secret_value(),
            self.tumblr_resource_owner_secret.get_secret_value(),
        )


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
        return all(block.type == "text" for block in self.content)

    def get_content_text(self) -> str:
        blocks = dict(enumerate(block.text for block in self.content))
        for block in self.layout:
            if block.type == "ask":
                for i in block.blocks:
                    del blocks[i]
        return "\n\n".join(blocks.values())


class Example(FullyValidatedModel):
    class Message(FullyValidatedModel):
        role: Literal["developer", "user", "assistant"]
        content: str

    messages: list[Message]
