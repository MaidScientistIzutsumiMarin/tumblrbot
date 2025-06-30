from collections.abc import Generator
from dataclasses import dataclass
from math import ceil
from pathlib import Path

import rich
from more_itertools import chunked
from rich.console import Console
from tiktoken import encoding_for_model, get_encoding

from tumblrbot.models import Example, Post
from tumblrbot.utils import PreviewLive, UtilClass, yes_no_prompt


@dataclass
class ExamplesWriter(UtilClass):
    download_paths: list[Path]

    def count_tokens(self) -> Generator[int]:
        # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
        # and https://cookbook.openai.com/examples/chat_finetuning_data_prep
        try:
            self.encoding = encoding_for_model(self.config.base_model)
        except KeyError as error:
            self.encoding = get_encoding("o200k_base")
            Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{self.encoding.name}': {''.join(error.args)}\n")

        with self.config.training.output_file.open(encoding="utf_8") as fp:
            for line in fp:
                example = Example.model_validate_json(line)
                yield 3 * (len(example.messages) + 1)  # every reply is primed with <|start|>assistant<|message|>

                for message in example.messages:
                    yield len(self.encoding.encode(message.content))

    def get_valid_posts(self) -> Generator[Post]:
        for download_path in self.download_paths:
            with download_path.open(encoding="utf_8") as fp:
                for line in fp:
                    post = Post.model_validate_json(line)
                    if post.get_text_content() and not (post.is_submission or post.trail):
                        yield post

    def get_filtered_posts(self) -> Generator[Post]:
        posts = list(self.get_valid_posts())
        n = 32  # Maybe get this dynamically in the future.

        if yes_no_prompt("Remove posts flagged by the OpenAI moderation? This can sometimes resolve errors with fine-tuning validation, but is slow."):
            with PreviewLive() as live:
                for chunk in live.progress.track(
                    chunked(posts, n),
                    ceil(len(posts) / n),
                    description="Removing flagged posts...",
                ):
                    response = self.openai.moderations.create(input=list(map(Post.get_text_content, chunk)))
                    for post, moderation in zip(chunk, response.results, strict=True):
                        if moderation.flagged:
                            live.custom_update(post)
                        else:
                            yield post
        else:
            yield from posts

    def write_examples(self) -> None:
        self.config.training.output_file.parent.mkdir(parents=True, exist_ok=True)
        posts = self.get_filtered_posts()

        with self.config.training.output_file.open("w", encoding="utf_8") as fp:
            for post in posts:
                example = Example(
                    messages=[
                        Example.Message(role="developer", content=self.config.developer_message),
                        Example.Message(role="user", content=self.config.user_input),
                        Example.Message(role="assistant", content=post.get_text_content()),
                    ],
                )
                fp.write(f"{example.model_dump_json()}\n")

        rich.print(f"[bold]The training data can be found at: '{self.config.training.output_file}'\n")
