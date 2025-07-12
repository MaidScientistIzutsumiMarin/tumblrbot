from collections.abc import Generator
from json import loads
from math import ceil
from re import search
from typing import IO, override

import rich
from more_itertools import chunked
from openai import BadRequestError
from rich.prompt import Confirm

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Example, Post


class ExamplesWriter(FlowClass):
    @override
    def main(self) -> None:
        self.config.examples_file.parent.mkdir(parents=True, exist_ok=True)

        with self.config.examples_file.open("w", encoding="utf_8") as fp:
            for user_message, assistant_response in self.get_custom_prompts():
                self.write_example(
                    user_message,
                    assistant_response,
                    fp,
                )

            for post in self.get_filtered_posts():
                self.write_example(
                    self.config.user_message,
                    post.get_content_text(),
                    fp,
                )

        rich.print(f"[bold]The examples file can be found at: '{self.config.examples_file}'\n")

    def write_example(self, user_message: str, assistant_message: str, fp: IO[str]) -> None:
        example = Example(
            messages=[
                Example.Message(role="developer", content=self.config.developer_message),
                Example.Message(role="user", content=user_message),
                Example.Message(role="assistant", content=assistant_message),
            ],
        )
        fp.write(f"{example.model_dump_json()}\n")

    def get_custom_prompts(self) -> Generator[tuple[str, str]]:
        self.config.custom_prompts_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.custom_prompts_file.touch(exist_ok=True)

        with self.config.custom_prompts_file.open("r", encoding="utf_8") as fp:
            for line in fp:
                data: dict[str, str] = loads(line)
                yield from data.items()

    def get_filtered_posts(self) -> Generator[Post]:
        posts = self.get_valid_posts()

        if Confirm.ask("[gray62]Remove posts flagged by the OpenAI moderation? This can sometimes resolve errors with fine-tuning validation, but is slow.", default=False):
            chunk_size = self.get_moderation_chunk_limit()
            posts = list(posts)
            removed = 0

            with PreviewLive() as live:
                for chunk in live.progress.track(
                    chunked(posts, chunk_size),
                    ceil(len(posts) / chunk_size),
                    description="Removing flagged posts...",
                ):
                    response = self.openai.moderations.create(input=list(map(Post.get_content_text, chunk)))
                    for post, moderation in zip(chunk, response.results, strict=True):
                        if moderation.flagged:
                            removed += 1
                            live.custom_update(post)
                        else:
                            yield post
            rich.print(f"[red]Removed {removed} posts.\n")
        else:
            yield from posts

    def get_valid_posts(self) -> Generator[Post]:
        for data_path in self.get_data_paths():
            with data_path.open(encoding="utf_8") as fp:
                for line in fp:
                    post = Post.model_validate_json(line)
                    if not (post.is_submission or post.trail) and post.only_text_blocks() and post.get_content_text():
                        yield post

    def get_moderation_chunk_limit(self) -> int:
        test_n = 1000
        try:
            self.openai.moderations.create(input=[""] * test_n)
        except BadRequestError as error:
            message = error.response.json()["error"]["message"]
            if match := search(r"(\d+)\.", message):
                return int(match.group(1))
        return test_n
