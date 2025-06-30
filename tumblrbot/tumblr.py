from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from secrets import token_urlsafe
from typing import Literal, Self, override

import rich
from httpx import URL, Auth, Client, HTTPStatusError, Request, Response
from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator
from pydantic.json_schema import SkipJsonSchema
from rich.panel import Panel
from rich.prompt import Prompt

from tumblrbot.settings import Tokens


class ConfiguredModel(BaseModel):
    model_config = ConfigDict(validate_default=True)


class Post(ConfiguredModel):
    class ContentBlock(ConfiguredModel):
        type: str
        text: str = ""

    class LayoutBlock(ConfiguredModel):
        type: str
        blocks: list[int] = []

    timestamp: SkipJsonSchema[NonNegativeInt] = 0
    is_submission: SkipJsonSchema[bool] = False
    tags: list[str] = []
    content: SkipJsonSchema[list[ContentBlock]] = []
    layout: SkipJsonSchema[list[LayoutBlock]] = []
    trail: SkipJsonSchema[list[object]] = []

    def __rich__(self) -> Panel:
        return Panel(
            self.get_text_content(),
            title="Preview",
            subtitle=" ".join(f"#{tag}" for tag in self.tags),
            subtitle_align="left",
        )

    @model_validator(mode="after")
    def filter_content(self) -> Self:
        ask_blocks = {*chain.from_iterable(block.blocks for block in self.layout if block.type == "ask")}
        self.content = [block for i, block in enumerate(self.content) if i not in ask_blocks and block.type == "text"]
        return self

    def get_text_content(self) -> str:
        return "\n\n".join(block.text for block in self.content)


class AuthorizationResponse(BaseModel):
    error_description: str = ""
    code: str
    state: str


class ErrorResponse(BaseModel):
    class Error(BaseModel):
        title: str
        code: int
        detail: str

        @override
        def __str__(self) -> str:
            return f"Subcode: {self.code} {self.title} ({self.detail})"

    errors: list[Error]


@dataclass
class TumblrClient(Client):
    tokens: Tokens
    token_time = datetime.min.replace(tzinfo=UTC)

    def __post_init__(self) -> None:
        super().__init__(
            auth=TumblrAuth(self),
            http2=True,
            event_hooks={
                "response": [self.response_hook],
            },
            base_url="https://api.tumblr.com/v2",
        )

    def response_hook(self, response: Response) -> None:
        try:
            response.raise_for_status()
        except HTTPStatusError as error:
            error_response = ErrorResponse.model_validate_json(error.response.read())
            for suberror in error_response.errors:
                error.add_note(str(suberror))
            raise

    @override
    def __enter__(self: Self) -> Self:
        super().__enter__()

        if self.tokens.tumblr.token.any_values_missing():
            state = token_urlsafe()
            url = URL(
                "https://tumblr.com/oauth2/authorize",
                params={
                    "client_id": self.tokens.tumblr.client_id,
                    "response_type": "code",
                    "scope": "basic write offline_access",
                    "state": state,
                },
            )

            rich.print(f"Go here and press 'Allow': {url}")
            response = AuthorizationResponse.model_validate(Prompt.ask("Paste the full redirected URL:"))
            if response.error_description or response.state != state:
                msg = f"Tumblr authorization failed! {response.error_description or 'State does not match.'}"
                raise RuntimeError(msg)

            self.tokens.tumblr.token = self.grant_token("authorization_code", response.code).json()
            self.tokens.model_post_init()

        return self

    def create_draft_post(self, blog_name: str, post: Post) -> Response:
        return self.post(
            f"blog/{blog_name}/posts",
            json={
                "content": list(map(dict, post.content)),
                "state": "draft",
                "tags": ",".join(post.tags),
            },
        )

    def retrieve_published_posts(self, blog_name: str, before: int) -> Response:
        return self.get(
            f"blog/{blog_name}/posts",
            params={
                "api_key": self.tokens.tumblr.client_id,
                "before": before,
                "npf": True,
            },
        )

    def grant_token(self, grant_type: Literal["authorization_code", "refresh_token"], code: str | None) -> Response:
        self.token_time = datetime.now(UTC)

        return self.post(
            "oauth2/token",
            data={
                "grant_type": grant_type,
                "code": code,
                "client_id": self.tokens.tumblr.client_id,
                "client_secret": self.tokens.tumblr.client_secret,
                "refresh_token": self.tokens.tumblr.token.refresh_token,
            },
            auth=lambda request: request,
        )


@dataclass
class TumblrAuth(Auth):
    client: TumblrClient

    @override
    def auth_flow(self, request: Request) -> Generator[Request, Response]:
        if datetime.now(UTC) >= self.client.token_time + self.client.tokens.tumblr.token.expires_in:
            self.client.tokens.tumblr.token = self.client.grant_token("refresh_token", None).json()
            self.client.tokens.model_post_init()

        request.headers["Authorization"] = f"Bearer {self.client.tokens.tumblr.token.access_token}"
        yield request
