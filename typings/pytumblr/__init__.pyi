from collections.abc import Collection
from typing import Literal, overload

from pytumblr.request import TumblrRequest
from requests import Response

class TumblrRestClient:
    request: TumblrRequest

    def __init__(self, consumer_key: str, consumer_secret: str, oauth_token: str, oauth_secret: str, host: str = "https://api.tumblr.com") -> None: ...
    @overload
    def create_text(
        self,
        blogname: str,
        *,
        state: Literal["published", "draft", "queue", "private"] = "published",
        tags: Collection[str] = [],
        tweet: object = None,
        date: object = None,
        format: Literal["html", "markdown"] = "html",
        slug: object = None,
        title: object,
        body: object,
    ) -> Response: ...
    @overload
    def create_text(
        self,
        blogname: str,
        *,
        state: Literal["published", "draft", "queue", "private"] = "published",
        tags: Collection[str] = [],
        tweet: object = None,
        date: object = None,
        format: Literal["html", "markdown"] = "html",
        slug: object = None,
        title: object,
    ) -> Response: ...
    @overload
    def create_text(
        self,
        blogname: str,
        *,
        state: Literal["published", "draft", "queue", "private"] = "published",
        tags: Collection[str] = [],
        tweet: object = None,
        date: object = None,
        format: Literal["html", "markdown"] = "html",
        slug: object = None,
        body: object,
    ) -> Response: ...
