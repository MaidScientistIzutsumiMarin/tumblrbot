from collections.abc import Collection, Generator, Iterable, Mapping
from json import dump
from pathlib import Path
from re import compile as re_compile
from sys import exit as sys_exit
from textwrap import dedent
from typing import IO, Any

from bs4 import BeautifulSoup
from rich import print as rich_print
from rich.progress import Progress
from tiktoken import encoding_for_model

from settings import Settings

IncomingMarkup = str | bytes | IO[str] | IO[bytes]


def count_tokens(messages: Collection[Mapping[Any, str]], settings: Settings) -> int:
    # Simplified from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    # Check there for a detailed explanation of what's being done here.
    encoding = encoding_for_model(settings.model_name)

    # Every reply is primed with <|start|>assistant<|message|>.
    tokens = 3 * (len(messages) + 1)
    for message in messages:
        for value in message.values():
            tokens += len(encoding.encode(value))
    return tokens


def build_messages(content: str, settings: Settings) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": settings.system_message,
        },
        {
            "role": "user",
            "content": settings.user_message,
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


def write_training_data(posts: Iterable[IncomingMarkup], settings: Settings) -> int:
    tokens = 0
    with settings.training.output_file.open("w", encoding="utf-8") as fp:
        for post in posts:
            if content := get_text(post):
                messages = build_messages(content, settings)
                training_data = {"messages": messages}

                # We think ensure_ascii is important here, but we don't know for sure. Having it should prevent any data loss.
                dump(training_data, fp, ensure_ascii=False)

                # Add a new line, since dump does not do this automatically.
                fp.write("\n")

                tokens += count_tokens(messages, settings)

    return tokens


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
    pattern = re_compile(dedent(text))

    with Progress() as progress:
        for file in Path("data").iterdir():
            text = file.read_text("utf-8")
            num_posts = text.count("Post id: ")
            yield from progress.track(pattern.findall(text), description=f"{file} [yellow]({num_posts} Posts)")


def main() -> None:
    settings = Settings()

    posts = get_posts()
    tokens = write_training_data(posts, settings)

    total_tokens = settings.training.expected_epochs * tokens

    text = f"""
        Total tokens {tokens:,}:
        Total tokens for [bold orange1]{settings.training.expected_epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{settings.model_name}[/]: ${3 / 1000000 * total_tokens:.2f}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]

        [bold]The training data has been written to the '{settings.training.output_file}' directory.
    """
    rich_print(dedent(text))


if __name__ == "__main__":
    sys_exit(main())
