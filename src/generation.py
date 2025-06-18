import sys
from collections.abc import Iterable
from itertools import islice
from random import choice, random

import rich
from openai import OpenAI
from pytumblr import TumblrRestClient
from rich._spinners import SPINNERS
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn
from rich.table import Table

from common import run_main

from settings import Env, Settings

SETTINGS = Settings()
ENV = Env()


def generate_tags(post_content: str, openai: OpenAI) -> list[str]:
    if random() > SETTINGS.generation.tags_chance:  # noqa: S311
        return []

    response = openai.responses.create(
        input="You are an advanced text summarization tool. You return the requested data to the user as a list of comma separated strings.",
        model=SETTINGS.model_name,
        instructions=f"Extract the most important subjects from the following text:\n\n{post_content}",
        max_output_tokens=50,
        temperature=0.5,
    )

    # Extract the text from the model's response and splitting into a list of strings.
    iterable = set(response.output_text.split(", "))

    # Get how many to extract.
    stop = min(len(iterable), SETTINGS.generation.max_num_tags)

    # Limit the number of subjects to the specified limit.
    return list(islice(iterable, stop))


def generate_text(openai: OpenAI) -> str:
    response = openai.responses.create(
        input=SETTINGS.system_message,
        model=ENV.openai_model.get_secret_value(),
        instructions=SETTINGS.user_message,
        max_output_tokens=4096 - len(SETTINGS.user_message.split()),
    )
    return response.output_text


def create_draft(openai: OpenAI, tumblr: TumblrRestClient) -> tuple[str, list[str]]:
    body = generate_text(openai)
    tags = generate_tags(body, openai)

    response = tumblr.create_text(
        ENV.blogname,
        state="draft",
        tags=tags or [""],
        format="markdown",
        body=body,
    )
    response.raise_for_status()

    return body, tags


def create_table(progress: Progress, body: str, tags: Iterable[str]) -> Table:
    tags_string = " ".join(f"#{tag}" for tag in tags)

    table = Table.grid(expand=True)
    table.add_row(progress)
    table.add_row(Panel(body, title="Preview", subtitle=tags_string, subtitle_align="left"))
    return table


def create_drafts(openai: OpenAI, tumblr: TumblrRestClient) -> int:
    spinner_name = choice(tuple(SPINNERS))  # noqa: S311
    progress = Progress(
        SpinnerColumn(spinner_name),
        *Progress.get_default_columns(),
        MofNCompleteColumn(),
        auto_refresh=False,
    )

    with Live(create_table(progress, "", [])) as live:
        for i in progress.track(range(SETTINGS.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr)
                live.update(create_table(progress, *draft))
            except BaseException:  # noqa: BLE001
                # Stop the live so that everything gets printed under it.
                live.stop()
                Console().print_exception()
                return i

    return SETTINGS.generation.draft_count


def get_tumblr_client() -> TumblrRestClient:
    tumblr = TumblrRestClient(
        ENV.tumblr_consumer_key.get_secret_value(),
        ENV.tumblr_consumer_secret.get_secret_value(),
        ENV.tumblr_oauth_token.get_secret_value(),
        ENV.tumblr_oauth_secret.get_secret_value(),
    )

    # Force pytumblr to return the raw Response object instead of a json.
    tumblr.request.json_parse = lambda response: response

    return tumblr


def main() -> None:
    openai = OpenAI(api_key=get_env().openai_api_key.get_secret_value())
    tumblr = get_tumblr_client()

    num_drafts = create_drafts(openai, tumblr)
    rich.print(f"[bold green]Generated {num_drafts} drafts! Check them out at:[/] https://tumblr.com/blog/{ENV.blogname}/drafts")


run_main(__name__, main)
