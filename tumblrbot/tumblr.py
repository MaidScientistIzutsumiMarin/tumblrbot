from pathlib import Path
from typing import Literal

import rich
from cachecontrol import CacheControl
from pydantic import BaseModel
from requests_oauthlib import OAuth1Session

from tumblrbot.settings import CONFIG, TOKENS, Tokens
from tumblrbot.utils import Post, PreviewLive, dump_model, print_token_url, token_prompt


class PostsResponse(BaseModel):
    class Response(BaseModel):
        class Blog(BaseModel):
            posts: int

        blog: Blog
        posts: list[Post]

    response: Response


class TumblrSession(OAuth1Session):
    def __init__(self) -> None:
        super().__init__(**TOKENS.tumblr.model_dump())

        CacheControl(self)

    def create_draft_post(self, post: Post) -> None:
        response = self.post(
            f"https://api.tumblr.com/v2/blog/{CONFIG.generation.blogname}/posts",
            data={
                "content": post.content,
                "state": "draft",
                "tags": post.tags,
            },
        )
        response.raise_for_status()

    def retrieve_published_posts(self, blogname: str, before: int) -> PostsResponse:
        response = self.get(
            f"https://api.tumblr.com/v2/blog/{blogname}/posts",
            params=sorted(
                {
                    "api_key": TOKENS.tumblr.client_key,
                    "before": before,
                    "npf": True,
                }.items(),
            ),
        )
        response.raise_for_status()
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

        output_paths = []
        completed = 0

        with PreviewLive(transient=not should_download) as live:
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
    print_token_url("https://platform.openai.com/settings/organization/api-keys", "consumer key", "consumer secret")
    consumer_key = token_prompt("consumer key")
    consumer_secret = token_prompt("consumer secret", secret=True)

    # STEP 1: Obtain request token
    session = OAuth1Session(consumer_key, consumer_secret)
    tokens = session.fetch_request_token("http://tumblr.com/oauth/request_token")

    # STEP 2: Authorize URL + Response
    authorization_url = session.authorization_url("http://tumblr.com/oauth/authorize")

    # Redirect to authentication page
    rich.print(f"\nGo here and press 'Allow': {authorization_url}")
    url = token_prompt("full redirected URL")

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
        client_secret=consumer_secret,
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )
    rich.print("[bold green]Successfully generated and saved tokens!\n")
