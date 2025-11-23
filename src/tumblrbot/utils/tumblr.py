from requests import HTTPError, Response, Session
from requests_oauthlib import OAuth1
from rich import print as rich_print
from tenacity import retry, retry_if_exception_message, stop_after_attempt, wait_random_exponential

from tumblrbot.utils.models import Post, ResponseModel, Tokens

rate_limit_retry = retry(
    stop=stop_after_attempt(10),
    wait=wait_random_exponential(min=60),
    retry=retry_if_exception_message(match="429 Client Error: Limit Exceeded for url: .+"),
    before_sleep=lambda state: rich_print(f"[yellow]Tumblr rate limit exceeded. Waiting for {state.idle_for} seconds..."),
    reraise=True,
)


class TumblrSession(Session):
    def __init__(self, tokens: Tokens) -> None:
        super().__init__()
        self.auth = OAuth1(**tokens.tumblr.model_dump())
        self.hooks["response"].append(self.response_hook)

        self.api_key = tokens.tumblr.client_key

    def response_hook(self, response: Response, *_args: object, **_kwargs: object) -> None:
        try:
            response.raise_for_status()
        except HTTPError as error:
            for error_msg in response.json()["errors"]:
                error.add_note(f"{error_msg['code']}: {error_msg['detail']}")
            raise

    @rate_limit_retry
    def retrieve_blog_info(self, blog_identifier: str) -> ResponseModel:
        response = self.get(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/info",
            params={
                "api_key": self.api_key,
            },
        )
        return ResponseModel.model_validate_json(response.text)

    @rate_limit_retry
    def retrieve_published_posts(
        self,
        blog_identifier: str,
        offset: int | None = None,
        after: int | None = None,
    ) -> ResponseModel:
        response = self.get(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            params={
                "api_key": self.api_key,
                "offset": offset,
                "after": after,
                "sort": "asc",
                "npf": True,
            },
        )
        return ResponseModel.model_validate_json(response.text)

    @rate_limit_retry
    def create_post(self, blog_identifier: str, post: Post) -> ResponseModel:
        response = self.post(
            f"https://api.tumblr.com/v2/blog/{blog_identifier}/posts",
            json=post.model_dump(),
        )
        return ResponseModel.model_validate_json(response.text)
