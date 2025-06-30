from collections.abc import Generator
from datetime import UTC, datetime
from json import dump
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal, Self, override

from hishel import CacheTransport, FileStorage
from httpx import URL, Auth, Client, HTTPTransport, Request, Response
from pydantic import BaseModel, NonNegativeInt

from tumblrbot.settings import CONFIG, TOKENS
from tumblrbot.utils import Post, PreviewLive, token_prompt


class AuthorizationResponse(BaseModel):
    error_description: str = ""
    code: str = ""
    state: str = ""


class PostsResponse(BaseModel):
    class Response(BaseModel):
        class Blog(BaseModel):
            posts: NonNegativeInt

        blog: Blog
        posts: list[dict[object, object]]

    response: Response


class TumblrAuth(Auth):
    def __init__(self, client: "TumblrSession") -> None:
        super().__init__()

        self.client = client
        self.token_time = datetime.min.replace(tzinfo=UTC)

    @override
    def auth_flow(self, request: Request) -> Generator[Request, Response]:
        if datetime.now(UTC) >= self.token_time + TOKENS.tumblr.token.expires_in:
            self.client.set_access_token("refresh_token", None)

        request.headers["Authorization"] = f"Bearer {TOKENS.tumblr.token.access_token}"
        yield request


class TumblrSession(Client):
    def __init__(self) -> None:
        super().__init__(
            auth=TumblrAuth(self),
            http2=True,
            event_hooks={
                "request": [],
                "response": [Response.raise_for_status],
            },
            base_url="https://api.tumblr.com/v2",
            transport=CacheTransport(
                HTTPTransport(),
                FileStorage(),
            ),
        )

        self.token_time = datetime.min.replace(tzinfo=UTC)

    def __enter__(self: Self) -> Self:
        super().__enter__()

        if TOKENS.tumblr.token.any_values_missing():
            state = token_urlsafe()
            url = URL(
                "https://tumblr.com/oauth2/authorize",
                params={
                    "client_id": TOKENS.tumblr.client_id,
                    "response_type": "code",
                    "scope": "basic write offline_access",
                    "state": state,
                },
            )

            (response,) = token_prompt(url, "full callback URL")
            response = AuthorizationResponse.model_validate(URL(response).params)
            if response.error_description or response.state != state:
                msg = f"Tumblr authorization failed! {response.error_description or 'State does not match.'}"
                raise RuntimeError(msg)

            self.set_access_token("authorization_code", response.code)

        return self

    def grant_token(self, grant_type: Literal["authorization_code", "refresh_token"], code: str | None) -> Response:
        return self.post(
            "oauth2/token",
            data={
                "grant_type": grant_type,
                "code": code,
                "client_id": TOKENS.tumblr.client_id,
                "client_secret": TOKENS.tumblr.client_secret,
                "refresh_token": TOKENS.tumblr.token.refresh_token,
            },
            auth=lambda request: request,
        )

    def create_draft_post(self, post: Post) -> Response:
        return self.post(
            f"blog/{CONFIG.generation.blog_name}/posts",
            data={
                "content": list(map(dict, post.content)),
                "state": "draft",
                "tags": ",".join(post.tags),
            },
        )

    def retrieve_published_posts(self, blog_name: str, before: int) -> Response:
        return self.get(
            f"blog/{blog_name}/posts",
            params={
                "api_key": TOKENS.tumblr.client_id,
                "before": before,
                "npf": True,
            },
        )

    def set_access_token(self, grant_type: Literal["authorization_code", "refresh_token"], code: str | None) -> None:
        self.token_time = datetime.now(UTC)
        TOKENS.tumblr.token = self.grant_token(grant_type, code).json()
        TOKENS.model_post_init()

    def write_published_posts_paginated(self, blog_name: str, before: int | Literal[False], completed: int, output_path: Path, live: PreviewLive) -> None:
        with output_path.open("a", encoding="utf_8") as fp:
            task_id = live.progress.add_task(f"Downloading posts from '{blog_name}'...", completed=completed)

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
