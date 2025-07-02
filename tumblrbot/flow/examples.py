from collections.abc import Generator
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from re import search

import rich
from more_itertools import chunked
from openai import BadRequestError
from rich.console import Console
from tiktoken import encoding_for_model, get_encoding

from tumblrbot.utils.common import PreviewLive, UtilClass, yes_no_prompt
from tumblrbot.utils.models import Example, Post


@dataclass
class ExamplesWriter(UtilClass):
    download_paths: list[Path]

    def count_tokens(self) -> Generator[int]:
        # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
        # and https://cookbook.openai.com/examples/chat_finetuning_data_prep
        try:
            encoding = encoding_for_model(self.config.base_model)
        except KeyError as error:
            encoding = get_encoding("o200k_base")
            Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {''.join(error.args)}\n")

        with self.config.training.output_file.open(encoding="utf_8") as fp:
            for line in fp:
                example = Example.model_validate_json(line)
                yield len(encoding.encode("assistant"))  # every reply is primed with <|start|>assistant<|message|>
                for message in example.messages:
                    yield 4 + len(encoding.encode(message.content))

    def get_moderation_chunk_limit(self) -> int:
        test_n = 1000
        try:
            self.openai.moderations.create(input=[""] * test_n)
        except BadRequestError as error:
            message = error.response.json()["error"]["message"]
            if match := search(r"(\d+)\.", message):
                return int(match.group(1))
        return test_n

    def get_valid_posts(self) -> Generator[Post]:
        for download_path in self.download_paths:
            with download_path.open(encoding="utf_8") as fp:
                for line in fp:
                    post = Post.model_validate_json(line)
                    if post.get_text_content() and not (post.is_submission or post.trail):
                        yield post

    def get_filtered_posts(self) -> Generator[Post]:
        posts = list(self.get_valid_posts())

        if yes_no_prompt("Remove posts flagged by the OpenAI moderation? This can sometimes resolve errors with fine-tuning validation, but is slow."):
            removed = 0
            chunk_size = self.get_moderation_chunk_limit()
            with PreviewLive() as live:
                for chunk in live.progress.track(
                    chunked(posts, chunk_size),
                    ceil(len(posts) / chunk_size),
                    description="Removing flagged posts...",
                ):
                    response = self.openai.moderations.create(input=list(map(Post.get_text_content, chunk)))
                    for post, moderation in zip(chunk, response.results, strict=True):
                        if moderation.flagged:
                            removed += 1
                            live.custom_update(post)
                        else:
                            yield post
            rich.print(f"[red]Removed {removed} posts.\n")
        else:
            yield from posts

    def write_examples(self) -> None:
        self.config.training.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config.training.output_file.open("w", encoding="utf_8") as fp:
            for post in self.get_filtered_posts():
                example = Example(
                    messages=[
                        Example.Message(role="developer", content=self.config.developer_message),
                        Example.Message(role="user", content=self.config.user_input),
                        Example.Message(role="assistant", content=post.get_text_content()),
                    ],
                )
                fp.write(f"{example.model_dump_json()}\n")

        rich.print(f"[bold]The training data can be found at: '{self.config.training.output_file}'\n")
