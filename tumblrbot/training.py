from collections.abc import Iterable
from pathlib import Path
from typing import IO

import rich
from rich.console import Console
from tiktoken import Encoding, encoding_for_model, get_encoding

from tumblrbot.openai_utils import print_estimates
from tumblrbot.settings import CONFIG
from tumblrbot.tumblr_utils import Post
from tumblrbot.utils import Example


def count_tokens(example: Example, encoding: Encoding) -> int:
    # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    # and https://cookbook.openai.com/examples/chat_finetuning_data_prep
    num_tokens = 3 * (len(example.messages) + 1)  # every reply is primed with <|start|>assistant<|message|>
    for message in example.messages:
        num_tokens += len(encoding.encode(message.content))
    return num_tokens


def write_examples(post: Post, encoding: Encoding, fp: IO[str], *, should_write: bool) -> int:
    if example := post.to_example():
        if should_write:
            fp.write(f"{example.model_dump_json()}\n")

        return count_tokens(example, encoding)
    return 0


def write_dataset(posts_paths: Iterable[Path], *, should_write: bool) -> int:
    try:
        encoding = encoding_for_model(CONFIG.base_model)
    except KeyError as error:
        encoding = get_encoding("o200k_base")
        Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {error.args[0]}\n")

    count = 0
    mode = "w" if should_write else "a"

    with CONFIG.training.output_file.open(mode, encoding="utf_8") as output_fp:
        for posts_path in posts_paths:
            with posts_path.open("r", encoding="utf_8") as post_fp:
                for line in post_fp:
                    post = Post.model_validate_json(line)
                    count += write_examples(post, encoding, output_fp, should_write=should_write)

    return count


def main(post_paths: Iterable[Path], *, should_write: bool) -> int:
    CONFIG.training.output_file.parent.mkdir(parents=True, exist_ok=True)

    tokens = write_dataset(post_paths, should_write=should_write)

    print_estimates(tokens)
    rich.print(f"[bold]The training data can be found at: '{CONFIG.training.output_file}'\n")

    return tokens
