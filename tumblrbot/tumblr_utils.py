from json import dump
from pathlib import Path
from typing import Any, Literal, override

import rich
from cachecontrol import CacheControl
from pydantic import BaseModel, NonNegativeInt
from requests import HTTPError, Response
from requests_oauthlib import OAuth2Session

from tumblrbot.settings import CONFIG, TOKENS
from tumblrbot.utils import Post, PreviewLive, token_prompt


class PostsResponse(BaseModel):
    class Response(BaseModel):
        class Blog(BaseModel):
            posts: NonNegativeInt

        blog: Blog
        posts: list[dict[object, object]]

    response: Response


class TumblrSession(OAuth2Session):
    def __init__(self) -> None:
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            TOKENS.tumblr.client_id,
            auto_refresh_url="https://api.tumblr.com/v2/oauth2/token",
            auto_refresh_kwargs={
                "client_id": TOKENS.tumblr.client_id,
                "client_secret": TOKENS.tumblr.client_secret,
            },
            token=TOKENS.tumblr.token,
            token_updater=write_token,
        )

        CacheControl(self)

    @override
    def request(self, *args: Any, **kwargs: object) -> Response:
        response = super().request(*args, **kwargs)  # pyright: ignore[reportUnknownMemberType]

        try:
            response.raise_for_status()
        except HTTPError as error:
            error.add_note(f"Full Response: {response.json()}")
            raise

        return response

    def create_draft_post(self, post: Post) -> Response:
        return self.post(
            f"https://api.tumblr.com/v2/blog/{CONFIG.generation.blog_name}/posts",
            json={
                "content": list(map(dict, post.content)),
                "state": "draft",
                "tags": ",".join(post.tags),
            },
        )

    def retrieve_published_posts(self, blog_name: str, before: int) -> Response:
        return self.get(
            f"https://api.tumblr.com/v2/blog/{blog_name}/posts",
            params=sorted(
                {
                    "api_key": TOKENS.tumblr.client_id,
                    "before": before,
                    "npf": True,
                }.items(),
            ),
        )

    def write_published_posts_paginated(self, blog_name: str, before: int | Literal[False], completed: int, output_path: Path, live: PreviewLive) -> None:
        with output_path.open("a", encoding="utf_8") as fp:
            task_id = live.progress.add_task(f"Downloading posts from '{blog_name}'...", total=None, completed=completed)

            while True:
                response = self.retrieve_published_posts(blog_name, before)
                response_object = PostsResponse.model_validate_json(response.text)

                for post in response_object.response.posts:
                    dump(post, fp)
                    fp.write("\n")

                    post_object = Post.model_validate(post)
                    before = post_object.timestamp

                    live.progress.update(task_id, advance=1)
                    live.custom_update(post_object)

                live.progress.update(task_id, total=response_object.response.blog.posts)

                if not response_object.response.posts:
                    break

    def write_all_published_posts(self, *, should_download: bool) -> None:
        CONFIG.training.data_directory.mkdir(parents=True, exist_ok=True)

        with PreviewLive(transient=not should_download) as live:
            for blog_name in CONFIG.training.blog_names:
                output_path = Post.get_posts_path(blog_name)

                before = False
                if output_path.exists():
                    lines = output_path.read_text("utf_8").splitlines()
                    completed = len(lines)
                    if lines:
                        before = Post.model_validate_json(lines[-1]).timestamp
                else:
                    completed = 0

                if should_download:
                    self.write_published_posts_paginated(
                        blog_name,
                        before,
                        completed,
                        output_path,
                        live,
                    )


def write_token(token: dict[str, object]) -> None:
    TOKENS.tumblr.token = token
    TOKENS.model_post_init()


def write_tumblr_credentials() -> None:
    TOKENS.tumblr.client_id, TOKENS.tumblr.client_secret = token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")

    oauth = OAuth2Session(TOKENS.tumblr.client_id, scope=["basic", "write", "offline_access"])
    authorization_url, _ = oauth.authorization_url("https://tumblr.com/oauth2/authorize")  # pyright: ignore[reportUnknownMemberType]
    (authorization_response,) = token_prompt(authorization_url, "full callback URL")

    token = oauth.fetch_token(  # pyright: ignore[reportUnknownMemberType]
        "https://api.tumblr.com/v2/oauth2/token",
        authorization_response=authorization_response,
        client_secret=TOKENS.tumblr.client_secret,
    )
    write_token(token)

    rich.print("[bold green]Successfully generated and saved tokens!\n")
