from dataclasses import dataclass

from requests import HTTPError, Response
from requests_oauthlib import OAuth1Session

from tumblrbot.utils.models import Post, Tokens


@dataclass
class TumblrClient(OAuth1Session):
    tokens: Tokens

    def __post_init__(self) -> None:
        super().__init__(*self.tokens.get_tumblr_tokens())
        self.hooks["response"].append(self.response_hook)

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
