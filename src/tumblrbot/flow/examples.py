from itertools import batched
from json import loads
from math import ceil
from re import IGNORECASE, search
from re import compile as re_compile
from typing import IO, TYPE_CHECKING, override

from openai import BadRequestError
from rich import print as rich_print

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Example, Post

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


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

            for post in self.get_valid_posts():
                self.write_example(
                    self.config.user_message,
                    str(post),
                    fp,
                )

        rich_print(f"[bold]The examples file can be found at: '{self.config.examples_file}'\n")

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

        with self.config.custom_prompts_file.open("rb") as fp:
            for line in fp:
                data: dict[str, str] = loads(line)
                yield from data.items()

    def get_valid_posts(self) -> Generator[Post]:
        for path in self.get_data_paths():
            posts = list(self.get_valid_posts_from_path(path))
            yield from posts[-self.config.post_limit :]

    def get_valid_posts_from_path(self, path: Path) -> Generator[Post]:
        pattern = re_compile("|".join(self.config.filtered_words), IGNORECASE)
        with path.open("rb") as fp:
            for line in fp:
                post = Post.model_validate_json(line)
                if post.valid_text_post() and not (post.trail and self.config.filtered_words and pattern.search(str(post))):
                    yield post

    def filter_examples(self) -> None:
        examples = self.config.examples_file.read_text("utf_8").splitlines()
        with self.config.examples_file.open("w", encoding="utf_8") as fp:
            batch_size = self.get_moderation_batch_size()
            removed = 0

            with PreviewLive() as live:
                for batch in live.progress.track(
                    batched(examples, batch_size, strict=False),
                    ceil(len(examples) / batch_size),
                    description="Removing flagged posts...",
                ):
                    response = self.openai.moderations.create(input=list(batch))
                    for example, moderation in zip(batch, response.results, strict=True):
                        if moderation.flagged:
                            removed += 1
                        else:
                            fp.write(f"{example}\n")
            rich_print(f"[red]Removed {removed} posts.\n")

    def get_moderation_batch_size(self) -> int:
        try:
            self.openai.moderations.create(input=[""] * self.config.max_moderation_batch_size)
        except BadRequestError as error:
            message = error.response.json()["error"]["message"]
            if match := search(r"(\d+)\.", message):
                return int(match.group(1))
        return self.config.max_moderation_batch_size
