from dataclasses import dataclass
from typing import Self

import rich
from requests import HTTPError, Response
from requests_oauthlib import OAuth2Session
from rich.prompt import Prompt

from tumblrbot.models import Post
from tumblrbot.settings import Tokens


@dataclass
class TumblrClient(OAuth2Session):
    tokens: Tokens

    def __post_init__(self) -> None:
        super().__init__(
            self.tokens.tumblr.client_id,
            auto_refresh_url="https://api.tumblr.com/v2/oauth2/token",
            auto_refresh_kwargs={
                "client_id": self.tokens.tumblr.client_id,
                "client_secret": self.tokens.tumblr.client_secret,
            },
            scope=["basic", "write", "offline_access"],
            token=self.tokens.tumblr.token,
            token_updater=self.token_saver,
        )

        self.hooks["response"].append(self.response_hook)

    def __enter__(self) -> Self:
        super().__enter__()

        if not self.tokens.tumblr.token:
            authorization_url, _ = self.authorization_url("https://tumblr.com/oauth2/authorize")

            rich.print(f"Please go to {authorization_url} and authorize access.")
            authorization_response = Prompt.ask("Enter the full callback URL")

            self.token_saver(
                self.fetch_token(
                    "https://api.tumblr.com/v2/oauth2/token",
                    authorization_response=authorization_response,
                    client_secret=self.tokens.tumblr.client_secret,
                ),
            )

        return self

    def token_saver(self, token: object) -> None:
        self.tokens.tumblr.token = token
        self.tokens.model_post_init()

    def response_hook(self, response: Response, **_: object) -> None:
        try:
            response.raise_for_status()
        except HTTPError as error:
            json = response.json()
            if error_description := json.get("error_description", None):
                error.add_note(error_description)
            elif errors := json.get("errors", None):
                for suberror in errors:
                    error.add_note(f"{suberror['title']} ({suberror['code']}): {suberror['detail']}")
            else:
                error.add_note(str(json))
            raise

    def create_draft_post(self, blog_name: str, post: Post) -> Response:
        return self.post(
            f"https://api.tumblr.com/v2/blog/{blog_name}/posts",
            json=post.model_dump(mode="json"),
        )

    def retrieve_published_posts(self, blog_name: str, before: int) -> Response:
        return self.get(
            f"https://api.tumblr.com/v2/blog/{blog_name}/posts",
            params={
                "before": before,
                "npf": True,
            },
        )
