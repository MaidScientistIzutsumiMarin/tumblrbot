from collections.abc import Generator
from itertools import batched
from json import loads
from math import ceil
from re import IGNORECASE
from re import compile as re_compile
from typing import TYPE_CHECKING, override

from rich import print as rich_print

from tumblrbot.actions.base import BaseAction
from tumblrbot.utils.common import PreviewLive, TumblrBotError, config, localize_number, warning_console
from tumblrbot.utils.models import Example, Message, Post

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable
    from pathlib import Path

    from openai._types import SequenceNotStr
    from openai.types import ModerationCreateResponse, ModerationMultiModalInputParam


class ExamplesWriter(BaseAction):
    @override
    def main(self) -> None:
        rich_print("[bold]Writing training data...")

        config.training_data_file.parent.mkdir(parents=True, exist_ok=True)

        examples = [self.create_example(*prompt) for prompt in self.get_custom_prompts()]
        examples.extend(self.create_example(config.user_message, str(post)) for post in self.get_valid_posts())

        if examples:
            self.write_examples(examples)
            rich_print(f"[bold]The training data can be found at: '{config.training_data_file}'\n")
        else:
            msg = "No valid posts found! [italic]Hint: Try downloading your latest posts..."
            raise TumblrBotError(msg)

    def create_example(self, user_message: str, assistant_message: str) -> Example:
        return Example(
            messages=[
                Message(role="developer", content=config.developer_message),
                Message(role="user", content=user_message),
                Message(role="assistant", content=assistant_message),
            ],
        )

    def get_custom_prompts(self) -> Generator[tuple[str, str]]:
        config.custom_prompts_file.parent.mkdir(parents=True, exist_ok=True)
        config.custom_prompts_file.touch(exist_ok=True)

        with config.custom_prompts_file.open("rb") as fp:
            for line in fp:
                data: dict[str, str] = loads(line)
                yield from data.items()

    # This function mostly exists to make writing examples (mostly) atomic.
    # If there is an error dumping the models or writing to the file,
    # then it will leave a partially written or empty file behind.
    def write_examples(self, examples: Iterable[Example]) -> None:
        with config.training_data_file.open("w", encoding="utf_8") as fp:
            for example in examples:
                fp.write(f"{example.model_dump_json()}\n")

    def get_valid_posts(self) -> Generator[Post]:
        for path in self.get_data_paths():
            if path.exists():
                posts = list(self.get_valid_posts_from_path(path))
                yield from posts[-config.post_limit :]
            else:
                warning_console.print(f"{path} does not exist!")

    def get_valid_posts_from_path(self, path: Path) -> Generator[Post]:
        earliest_timestamp = config.date_limit.timestamp()
        pattern = re_compile("|".join(config.filtered_words), IGNORECASE)
        with path.open("rb") as fp:
            for line in fp:
                post = Post.model_validate_json(line)
                if post.valid_text_post() and post.timestamp >= earliest_timestamp and not (post.trail and config.filtered_words and pattern.search(str(post))):
                    yield post

    def filter_examples(self) -> None:
        raw_examples = config.training_data_file.read_bytes().splitlines()
        old_examples = map(Example.model_validate_json, raw_examples)
        new_examples: list[Example] = []
        with PreviewLive() as live:
            for batch in live.progress.track(
                batched(old_examples, config.moderation_batch_size, strict=False),
                ceil(len(raw_examples) / config.moderation_batch_size),
                description="Removing flagged posts...",
            ):
                response = self.create_moderation_batch(tuple(map(Example.get_assistant_message, batch)))
                new_examples.extend(example for example, moderation in zip(batch, response.results, strict=True) if not moderation.flagged)

        self.write_examples(new_examples)

        rich_print(f"[green]Removed {localize_number(len(raw_examples) - len(new_examples))} posts.\n")

    def create_moderation_batch(self, api_input: str | SequenceNotStr[str] | Iterable[ModerationMultiModalInputParam]) -> ModerationCreateResponse:
        return self.openai.moderations.create(input=api_input)
