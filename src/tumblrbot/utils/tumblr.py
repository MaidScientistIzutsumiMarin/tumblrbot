from dataclasses import dataclass

from pydantic import Secret
from requests import HTTPError, Response
from requests_oauthlib import OAuth2Session

from tumblrbot.utils.models import Post
from tumblrbot.utils.settings import Tokens


@dataclass
class TumblrClient(OAuth2Session):
    tokens: Tokens

    def __post_init__(self) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            self.tokens.tumblr_client_id.get_secret_value(),
            auto_refresh_url="https://api.tumblr.com/v2/oauth2/token",
            auto_refresh_kwargs={
                "client_id": self.tokens.tumblr_client_id.get_secret_value(),
                "client_secret": self.tokens.tumblr_client_secret.get_secret_value(),
                "token": self.tokens.tumblr_token.get_secret_value(),
            },
            token=self.tokens.tumblr_token.get_secret_value(),
            token_updater=self.token_updater,
        )

        self.hooks["response"].append(self.response_hook)

    def token_updater(self, token: object) -> None:
        self.tokens.tumblr_token = Secret(token)

    def response_hook(self, response: Response, **_: object) -> None:
        try:
            response.raise_for_status()
        except HTTPError as error:
            error.add_note(response.text)
            raise

    def retrieve_published_posts(self, blog_identifier: str, after: int) -> Response:
        return self.get(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            params={
                "after": after,
                "sort": "asc",
                "npf": True,
            },
        )

    def create_post(self, blog_identifier: str, post: Post) -> Response:
        return self.post(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            json=post.model_dump(mode="json"),
        )
