from typing import Self

from requests import HTTPError, Response
from requests_oauthlib import OAuth1Session

from tumblrbot.utils.models import Post, ResponseModel, Tokens


class TumblrSession(OAuth1Session):
    def __init__(self, tokens: Tokens) -> None:
        super().__init__(**tokens.tumblr.model_dump())
        self.hooks["response"].append(self.response_hook)

    def __enter__(self) -> Self:
        super().__enter__()
        return self

    def response_hook(self, response: Response, *_args: object, **_kwargs: object) -> None:
        try:
            response.raise_for_status()
        except HTTPError as error:
            error.add_note(response.text)
            raise

    def retrieve_published_posts(self, blog_identifier: str, after: int) -> ResponseModel:
        response = self.get(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            params={
                "after": after,
                "sort": "asc",
                "npf": True,
            },
        )
        return ResponseModel.model_validate_json(response.content)

    def create_post(self, blog_identifier: str, post: Post) -> ResponseModel:
        response = self.post(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            json=post.model_dump(),
        )
        return ResponseModel.model_validate_json(response.content)
