from collections.abc import Generator
from itertools import batched
from json import loads
from math import ceil
from re import IGNORECASE
from re import compile as re_compile
from typing import TYPE_CHECKING, override

from openai import RateLimitError
from rich import print as rich_print
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Example, Message, Post

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from pathlib import Path

    from openai._types import SequenceNotStr
    from openai.types import ModerationCreateResponse, ModerationMultiModalInputParam


class ExamplesWriter(FlowClass):
    @override
    def main(self) -> None:
        self.config.examples_file.parent.mkdir(parents=True, exist_ok=True)

        examples = [self.create_example(*prompt) for prompt in self.get_custom_prompts()]
        examples.extend(self.create_example(self.config.user_message, str(post)) for post in self.get_valid_posts())
        self.write_examples(examples)

        rich_print(f"[bold]The examples file can be found at: '{self.config.examples_file}'\n")

    def create_example(self, user_message: str, assistant_message: str) -> Example:
        return Example(
            messages=[
                Message(role="developer", content=self.config.developer_message),
                Message(role="user", content=user_message),
                Message(role="assistant", content=assistant_message),
            ],
        )

    def get_custom_prompts(self) -> Generator[tuple[str, str]]:
        self.config.custom_prompts_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.custom_prompts_file.touch(exist_ok=True)

        with self.config.custom_prompts_file.open("rb") as fp:
            for line in fp:
                data: dict[str, str] = loads(line)
                yield from data.items()

    # This function mostly exists to make writing examples atomic.
    def write_examples(self, examples: Iterable[Example]) -> None:
        with self.config.examples_file.open("w", encoding="utf_8") as fp:
            for example in examples:
                fp.write(f"{example.model_dump_json()}\n")

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
        raw_examples = self.config.examples_file.read_bytes().splitlines()
        old_examples = map(Example.model_validate_json, raw_examples)
        new_examples: list[Example] = []
        with PreviewLive() as live:
            for batch in live.progress.track(
                batched(old_examples, self.config.max_moderation_batch_size, strict=False),
                ceil(len(raw_examples) / self.config.max_moderation_batch_size),
                description="Removing flagged posts...",
            ):
                response = self.create_moderation_batch(tuple(map(Example.get_assistant_message, batch)))
                new_examples.extend(example for example, moderation in zip(batch, response.results, strict=True) if not moderation.flagged)

        self.write_examples(new_examples)

        rich_print(f"[red]Removed {len(raw_examples) - len(new_examples)} posts.\n")

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_random_exponential(),
        retry=retry_if_exception_type(RateLimitError),
        before_sleep=lambda state: rich_print(f"[yellow]OpenAI rate limit exceeded. Waiting for {state.idle_for} seconds..."),
        reraise=True,
    )
    def create_moderation_batch(self, api_input: str | SequenceNotStr[str] | Iterable[ModerationMultiModalInputParam]) -> ModerationCreateResponse:
        return self.openai.moderations.create(input=api_input)
