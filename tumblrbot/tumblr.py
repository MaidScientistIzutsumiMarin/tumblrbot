from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from typing import Self, override

from authlib.integrations.httpx_client import OAuth2Client
from httpx import HTTPStatusError, Response
from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator
from pydantic.json_schema import SkipJsonSchema
from rich.panel import Panel

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
class TumblrClient(OAuth2Client):
    tokens: Tokens
    token_time = datetime.min.replace(tzinfo=UTC)

    def __post_init__(self) -> None:
        super().__init__(
            **self.tokens.tumblr.model_dump(),
            token_endpoint="https://api.tumblr.com/v2/oauth2/token",
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
