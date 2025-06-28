from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from rich.console import Console
from tiktoken import Encoding, encoding_for_model, get_encoding

from tumblrbot.settings import CONFIG
from tumblrbot.tumblr import Post
from tumblrbot.utils import dedent_print, get_cost_string


class Example(BaseModel):
    class Message(BaseModel):
        content: str
        role: Literal["user", "assistant"]

    messages: list[Message]


def count_tokens(example: Example, encoding: Encoding) -> int:
    # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    # and https://cookbook.openai.com/examples/chat_finetuning_data_prep

    # Not 100% accurate... Estimates it a few hundred tokens too high. It was accurate when it was given a block of text.

    num_tokens = 3 * (len(example.messages) + 1)  # every reply is primed with <|start|>assistant<|message|>
    for message in example.messages:
        num_tokens += len(encoding.encode(message.content))
    return num_tokens


def write_example(post: Post, encoding: Encoding, *, should_write: bool) -> int:
    if not (post.is_submission or post.trail) and post.content:
        example = Example(
            messages=[
                Example.Message(
                    role="user",
                    content=CONFIG.user_message,
                ),
                Example.Message(
                    role="assistant",
                    content=post.model_dump_json(),
                ),
            ],
        )

        if should_write:
            with CONFIG.training.output_file.open("a", encoding="utf_8") as fp:
                fp.write(f"{example.model_dump_json()}\n")

        return count_tokens(example, encoding)
    return 0


def write_dataset(posts_paths: Iterable[Path], *, should_write: bool) -> int:
    try:
        encoding = encoding_for_model(CONFIG.model_name)
    except KeyError as error:
        encoding = get_encoding("o200k_base")
        Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {error.args[0]}\n")

    count = 0

    for posts_path in posts_paths:
        with posts_path.open("r", encoding="utf_8") as post_fp:
            for line in post_fp:
                post = Post.model_validate_json(line)
                count += write_example(post, encoding, should_write=should_write)

    return count


def main(post_paths: Iterable[Path], *, should_write: bool) -> int:
    CONFIG.training.output_file.parent.mkdir(parents=True, exist_ok=True)

    if should_write:
        CONFIG.training.output_file.unlink()

    tokens = write_dataset(post_paths, should_write=should_write)
    total_tokens = CONFIG.training.estimated_epochs * tokens

    dedent_print(f"""
        Total tokens {tokens:,}:
        Total tokens for [bold orange1]{CONFIG.training.estimated_epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{CONFIG.model_name}[/]: {get_cost_string(total_tokens)}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]

        [bold]The training data can be found at: '{CONFIG.training.output_file}'
    """)

    return tokens
