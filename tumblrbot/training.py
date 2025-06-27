from collections.abc import Generator, Iterable
from pathlib import Path
from textwrap import dedent
from typing import Literal

import rich
from pydantic import BaseModel
from rich.console import Console
from tiktoken import encoding_for_model, get_encoding

from tumblrbot.settings import CONFIG
from tumblrbot.tumblr import Post
from tumblrbot.utils import PreviewLive, dump_model


class Messages(BaseModel):
    class Message(BaseModel):
        role: Literal["user", "assistant"]
        content: str

    messages: list[Message]


def count_tokens(dataset: Iterable[Messages]) -> int:
    # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    # and https://cookbook.openai.com/examples/chat_finetuning_data_prep

    try:
        encoding = encoding_for_model(CONFIG.model_name)
    except KeyError as error:
        encoding = get_encoding("o200k_base")
        Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {error.args[0]}")

    tokens = 0
    for training_data in dataset:
        for message in training_data.messages:
            tokens += 3 + len(encoding.encode(message.content))
        tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return tokens


def build_messages(content: str) -> Messages:
    return Messages(
        messages=[
            Messages.Message(role="user", content=CONFIG.user_message),
            Messages.Message(role="assistant", content=content),
        ],
    )


def get_posts(posts_paths: Iterable[Path]) -> Generator[Post]:
    for posts_path in posts_paths:
        with posts_path.open("rb") as fp:
            yield from map(Post.model_validate_json, fp)


def write_training_data(posts_paths: Iterable[Path], total: int) -> Generator[Messages]:
    with CONFIG.training.output_file.open("wb") as fp, PreviewLive() as live:
        for post in live.progress.track(
            get_posts(posts_paths),
            total=total,
            description="Writing training data...",
        ):
            if not post.trail and (content := post.get_text_content()):
                training_data = build_messages(content)
                yield training_data

                dump_model(training_data, fp)

                live.custom_update(post)


def main(post_paths: Iterable[Path], total: int) -> None:
    CONFIG.training.output_file.parent.mkdir(parents=True, exist_ok=True)

    dataset = write_training_data(post_paths, total)
    tokens = count_tokens(dataset)

    total_tokens = CONFIG.training.target_epochs * tokens

    text = f"""
        Total tokens {tokens:,}:
        Total tokens for [bold orange1]{CONFIG.training.target_epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{CONFIG.model_name}[/]: ${CONFIG.training.token_price / 1000000 * total_tokens:.2f}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]

        [bold]The training data has been written to the '{CONFIG.training.output_file}' directory.
    """
    rich.print(dedent(text))
