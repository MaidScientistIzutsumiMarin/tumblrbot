from pathlib import Path
from typing import Any, Literal, override
from urllib.parse import urljoin

import rich
import rich.pretty
from cachecontrol import CacheControl
from pydantic import BaseModel, Secret
from requests import Response
from requests_oauthlib import OAuth1Session
from rich.prompt import Prompt

from tumblrbot.settings import CONFIG, TOKENS, Tokens
from tumblrbot.utils import Post, PreviewLive, dump_model


class PostsResponse(BaseModel):
    class Response(BaseModel):
        class Blog(BaseModel):
            posts: int

        blog: Blog
        posts: list[Post]

    response: Response


class TumblrSession(OAuth1Session):
    def __init__(self) -> None:
        super().__init__(
            TOKENS.tumblr.client_key,
            TOKENS.tumblr.client_secret.get_secret_value(),
            TOKENS.tumblr.resource_owner_key,
            TOKENS.tumblr.resource_owner_secret.get_secret_value(),
        )

        # The returned session is actually just the same as the passed session.
        CacheControl(self)

        self.base_url = "https://api.tumblr.com/v2/blog/"

    @override
    def request(self, method: str | bytes, url: str | bytes, *args: Any, **kwargs: object) -> Response:
        response = super().request(
            method,
            urljoin(self.base_url, url if isinstance(url, str) else url.decode()),
            *args,
            **kwargs,
        )

        # TODO: Remove
        if not response.ok:
            rich.pretty.pprint(response.json())
            input()

        response.raise_for_status()
        return response

    def create_draft_post(self, content: list[str], tags: str) -> Response:
        return self.post(
            f"{CONFIG.generation.blogname}/posts",
            data={
                "content": content,
                "state": "draft",
                "tags": tags,
            },
        )

    def retrieve_published_posts(self, blogname: str, before: int) -> PostsResponse:
        response = self.get(
            f"{blogname}/posts",
            params={
                "api_key": TOKENS.tumblr.client_key,
                "before": before,
                "npf": True,
            },
        )
        return PostsResponse.model_validate_json(response.content)

    def write_published_posts_paginated(self, blogname: str, before: int | Literal[False], completed: int, output_path: Path, live: PreviewLive) -> int:
        with output_path.open("ab") as fp:
            task_id = live.progress.add_task(f"Downloading posts from '{blogname}'...", total=0)

            while True:
                response = self.retrieve_published_posts(blogname, before)
                if not response.response.posts:
                    return completed

                for post in response.response.posts:
                    dump_model(post, fp)
                    before = post.timestamp

                # Update at the end instead of in the loop to not waste performance.
                completed += len(response.response.posts)
                live.progress.update(task_id, total=response.response.blog.posts, completed=completed)
                live.custom_update(response.response.posts[-1])

    def write_all_published_posts(self, *, should_download: bool) -> tuple[list[Path], int]:
        CONFIG.training.data_directory.mkdir(parents=True, exist_ok=True)

        output_paths: list[Path] = []
        completed = 0

        with PreviewLive() as live:
            for blogname in CONFIG.training.blognames:
                output_path = (CONFIG.training.data_directory / blogname).with_suffix(".jsonl")

                if output_path.exists():
                    output_paths.append(output_path)

                    lines = output_path.read_bytes().splitlines()
                    before = Post.model_validate_json(lines[-1]).timestamp
                    already_downloaded = len(lines)
                else:
                    before = False
                    already_downloaded = 0

                if should_download:
                    completed += self.write_published_posts_paginated(
                        blogname,
                        before,
                        already_downloaded,
                        output_path,
                        live,
                    )
                else:
                    completed += already_downloaded

        return output_paths, completed


def write_tumblr_credentials() -> None:
    rich.print("Retrieve a consumer key and consumer secret from: http://tumblr.com/oauth/apps")
    consumer_key = Prompt.ask("Enter the consumer key").strip()
    consumer_secret = Prompt.ask("Enter the consumer secret [yellow](hidden)", password=True).strip()

    # STEP 1: Obtain request token
    session = OAuth1Session(consumer_key, consumer_secret)
    tokens = session.fetch_request_token("http://tumblr.com/oauth/request_token")

    # STEP 2: Authorize URL + Response
    authorization_url = session.authorization_url("http://tumblr.com/oauth/authorize")

    # Redirect to authentication page
    rich.print(f"\nGo here and press 'Allow': {authorization_url}")
    url = Prompt.ask("Enter the full redirected URL").strip()

    # STEP 3: Request final access token
    session = OAuth1Session(
        consumer_key,
        consumer_secret,
        tokens["oauth_token"],
        tokens["oauth_token_secret"],
        verifier=session.parse_authorization_response(url)["oauth_verifier"],
    )
    tokens = session.fetch_access_token("http://tumblr.com/oauth/access_token")

    TOKENS.tumblr = Tokens.Tumblr(
        client_key=consumer_key,
        client_secret=Secret(consumer_secret),
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )
    rich.print("[bold green]Successfully generated and saved tokens!\n")
