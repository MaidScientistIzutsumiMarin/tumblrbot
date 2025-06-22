import re
from collections.abc import Collection, Generator, Iterable, Mapping, Sized
from json import dump
from pathlib import Path
from textwrap import dedent
from typing import IO

import rich
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress
from tiktoken import encoding_for_model, get_encoding

from common import run_main
from settings import SETTINGS

IncomingMarkup = str | bytes | IO[str] | IO[bytes]


def count_epochs(messages: Sized) -> int:
    # Based on https://cookbook.openai.com/examples/chat_finetuning_data_prep

    min_target_examples = 100
    max_target_examples = 25000

    target_epochs = 3
    n_train_examples = len(messages)
    if n_train_examples * target_epochs < min_target_examples:
        return min(25, min_target_examples // n_train_examples)
    if n_train_examples * target_epochs > max_target_examples:
        return max(1, max_target_examples // n_train_examples)
    return target_epochs


def count_tokens(dataset: Iterable[Collection[Mapping[str, str]]]) -> int:
    # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    # and https://cookbook.openai.com/examples/chat_finetuning_data_prep

    try:
        encoding = encoding_for_model(SETTINGS.model_name)
    except KeyError as exc:
        encoding = get_encoding("o200k_base")
        Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {exc.args[0]}")

    total_tokens = 0
    for messages in dataset:
        messages_tokens = 3 * (len(messages) + 1)  # every reply is primed with <|start|>assistant<|message|>
        for message in messages:
            for value in message.values():
                messages_tokens += len(encoding.encode(value))
        total_tokens += min(SETTINGS.training.max_output_tokens, messages_tokens)
    return total_tokens


def build_messages(content: str) -> list[dict[str, str]]:
    return [
        {
            "role": "developer",
            "content": SETTINGS.developer_message,
        },
        {
            "role": "user",
            "content": SETTINGS.user_message,
        },
        {
            "role": "assistant",
            "content": content,
        },
    ]


def get_text(post: IncomingMarkup) -> str:
    soup = BeautifulSoup(post, "lxml")

    # Remove the classes specified which only contain garbage data that would be picked up as text.
    # It would be possible to use an inverted regex or lambda to instead iterate through all classes besides these,
    # but that would be a fair bit more complicated and harder to read.
    for element in soup.find_all(class_=("tmblr-alt-text-helper", "poll-question", "poll-row", "poll-see-results")):
        element.decompose()

    return soup.get_text(" ", strip=True)


def write_training_data(posts: Iterable[IncomingMarkup]) -> Generator[list[dict[str, str]]]:
    with SETTINGS.training.output_file.open("w", encoding="utf-8") as fp:
        for post in posts:
            if content := get_text(post):
                messages = build_messages(content)
                training_data = {"messages": messages}

                # We think ensure_ascii is important here, but we don't know for sure. Having it should prevent any data loss.
                dump(training_data, fp, ensure_ascii=False)

                # Add a new line, since dump does not do this automatically.
                fp.write("\n")

                yield messages


def get_posts() -> Generator[str]:
    # Specifically look for empty Reblog urls and names.
    # The Body can span multiple lines.
    text = r"""
        Reblog url:\s
        Reblog name:\s
        Title:.+
        Body:\s([\s\S]*?)
        Tags:
    """.lstrip("\n").rstrip()
    pattern = re.compile(dedent(text))

    with Progress() as progress:
        for file in Path(SETTINGS.training.data_directory).iterdir():
            text = file.read_text("utf-8")
            num_posts = text.count("Post id: ")
            yield from progress.track(pattern.findall(text), description=f"{file} [yellow]({num_posts} Posts)")


def create_directories() -> None:
    SETTINGS.training.data_directory.mkdir(parents=True, exist_ok=True)
    SETTINGS.training.output_file.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    create_directories()
    posts = get_posts()
    training_data = tuple(write_training_data(posts))

    epochs = count_epochs(training_data)
    tokens = count_tokens(training_data)
    total_tokens = epochs * tokens

    text = f"""
        Total tokens {tokens:,}:
        Total tokens for [bold orange1]{epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{SETTINGS.model_name}[/]: ${SETTINGS.training.token_price / 1000000 * total_tokens:.2f}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]

        [bold]The training data has been written to the '{SETTINGS.training.output_file}' directory.
    """
    rich.print(dedent(text))


run_main(__name__, main)
