from collections.abc import Collection, Generator, Iterable, Mapping
from json import dump, load
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run
from textwrap import dedent

import rich
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from tiktoken import encoding_for_model, get_encoding
from tumblr_backup.main import EXIT_NOPOSTS

from common import CustomLive, run_main
from settings import ENV, SETTINGS


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
            "role": "user",
            "content": SETTINGS.user_message,
        },
        {
            "role": "assistant",
            "content": content,
        },
    ]


def get_content(post_path: Path) -> str:
    with post_path.open(encoding="utf-8") as fp:
        post = load(fp)

    soup = BeautifulSoup(post["body"], "lxml")

    # Remove the classes specified which only contain garbage data that would be picked up as text.
    for element in soup(class_="tmblr-alt-text-helper"):
        element.decompose()

    return soup.get_text(" ", strip=True)


def write_training_data(post_paths: Iterable[Path]) -> Generator[list[dict[str, str]]]:
    with SETTINGS.training.output_file.open("w", encoding="utf-8") as fp, CustomLive() as live:
        for post_path in live.progress.track(post_paths, description="Writing training data..."):
            if content := get_content(post_path):
                live.custom_update(content)

                messages = build_messages(content)
                training_data = {"messages": messages}

                # We think ensure_ascii is important here, but we don't know for sure. Having it should prevent any data loss.
                dump(training_data, fp, ensure_ascii=False)

                # Add a new line, since dump does not do this automatically.
                fp.write("\n")

                yield messages


def download_posts() -> list[Path]:
    yes_option = "y"
    should_download = Prompt.ask("Download latest posts?", choices=[yes_option, "n"], case_sensitive=False, default=yes_option) == yes_option

    tumblr_backup_filename = "tumblr-backup"
    tumblr_backup_path = which(tumblr_backup_filename) or ""

    try:
        run(
            [tumblr_backup_path, "--set-api-key", ENV.tumblr_consumer_key.get_secret_value()],
            check=True,
        )
    except FileNotFoundError as error:
        error.filename = tumblr_backup_filename
        raise

    post_paths: list[Path] = []
    for blogname in SETTINGS.training.blognames:
        output_directory = SETTINGS.training.data_directory / blogname

        if should_download:
            try:
                run(
                    [tumblr_backup_path, blogname, "--outdir", output_directory, "--incremental", "--skip-images", "--json", "--type", "text", "--no-reblog"],
                    check=True,
                )
            except CalledProcessError as error:
                if error.returncode != EXIT_NOPOSTS:
                    raise

        post_paths += (output_directory / "json").iterdir()
    return post_paths


def main() -> None:
    SETTINGS.training.output_file.parent.mkdir(parents=True, exist_ok=True)

    post_paths = download_posts()
    training_data = write_training_data(post_paths)

    tokens = count_tokens(training_data)
    total_tokens = SETTINGS.training.target_epochs * tokens

    text = f"""
        Total tokens {tokens:,}:
        Total tokens for [bold orange1]{SETTINGS.training.target_epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{SETTINGS.model_name}[/]: ${SETTINGS.training.token_price / 1000000 * total_tokens:.2f}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]

        [bold]The training data has been written to the '{SETTINGS.training.output_file}' directory.
    """
    rich.print(dedent(text))


run_main(__name__, main)
