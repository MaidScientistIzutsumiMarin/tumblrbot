from dataclasses import dataclass

from authlib.integrations.httpx_client import OAuth2Client
from httpx import HTTPStatusError, Response

from tumblrbot.models import ErrorResponse, Post
from tumblrbot.settings import Tokens


@dataclass
class TumblrClient(OAuth2Client):
    tokens: Tokens

    def __post_init__(self) -> None:
        super().__init__(
            **self.tokens.tumblr.model_dump(),
            token_endpoint="https://api.tumblr.com/v2/oauth2/token",  # noqa: S106
            http2=True,
            event_hooks={"response": [self.response_hook]},
            base_url="https://api.tumblr.com/v2",
            update_token=self.update_token,
        )

    def update_token(self, token: object) -> None:
        self.tokens.tumblr.token = token
        self.tokens.model_post_init()

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
                "content": post.content,
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
