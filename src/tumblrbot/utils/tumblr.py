from dataclasses import dataclass
from typing import Self

from niquests import HTTPError, PreparedRequest, Response, Session
from requests_oauthlib import OAuth1

from tumblrbot.utils.models import Post, Tokens


@dataclass
class TumblrSession(Session):
    tokens: Tokens

    def __post_init__(self) -> None:
        super().__init__(multiplexed=True, happy_eyeballs=True)

        self.auth = OAuth1(**self.tokens.tumblr.model_dump(mode="json"))
        self.hooks["response"].append(self.response_hook)

    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def response_hook(self, response: PreparedRequest | Response) -> None:
        if isinstance(response, Response):
            try:
                response.raise_for_status()
            except HTTPError as error:
                if response.text:
                    error.add_note(response.text)
                raise

    def retrieve_published_posts(self, blog_identifier: str, after: int) -> Response:
        return self.get(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            params={
                "after": str(after),
                "sort": "asc",
                "npf": str(True),
            },
        )

    def create_post(self, blog_identifier: str, post: Post) -> Response:
        return self.post(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            json=post.model_dump(mode="json"),
        )
