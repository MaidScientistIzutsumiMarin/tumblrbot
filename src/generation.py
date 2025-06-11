import random
from collections.abc import Iterable
from sys import exit as sys_exit

from openai import OpenAI
from pytumblr import TumblrRestClient
from rich import print as rich_print
from rich._spinners import SPINNERS
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn
from rich.table import Table

from settings import Settings


def generate_tags(post_content: str, openai: OpenAI, settings: Settings) -> list[str]:
    if random.random() > settings.generation.tags_chance:  # noqa: S311
        return []

    response = openai.responses.create(
        input="You are an advanced text summarization tool. You return the requested data to the user as a list of comma separated strings.",
        model=settings.model_name,
        instructions=f"Extract the most important subjects from the following text:\n\n{post_content}",
        max_output_tokens=50,
        temperature=0.5,
    )

    # Extracting the text from the model's response.
    extracted_subjects = response.output_text

    # Splitting into a list of strings.
    subjects_list = extracted_subjects.split(", ")

    # Limiting the number of subjects to the specified limit.
    if len(subjects_list) > settings.generation.max_num_tags:
        return random.sample(subjects_list, settings.generation.max_num_tags)
    return subjects_list


def generate_text(openai: OpenAI, settings: Settings) -> str:
    response = openai.responses.create(
        input=settings.system_message,
        model=settings.env.openai_model.get_secret_value(),
        instructions=settings.user_message,
        max_output_tokens=4096 - len(settings.user_message.split()),
    )
    return response.output_text


def create_draft(openai: OpenAI, tumblr: TumblrRestClient, settings: Settings) -> tuple[str, list[str]]:
    body = generate_text(openai, settings)
    tags = generate_tags(body, openai, settings)

    response = tumblr.create_text(
        settings.env.blogname,
        state="draft",
        body=body,
        tags=tags or [""],
    )
    response.raise_for_status()

    return body, tags


def create_table(progress: Progress, body: str, tags: Iterable[str]) -> Table:
    tags_string = " ".join(f"#{tag}" for tag in tags)

    table = Table.grid(expand=True)
    table.add_row(progress)
    table.add_row(Panel(body, title="Preview", subtitle=tags_string, subtitle_align="left"))
    return table


def create_drafts(openai: OpenAI, tumblr: TumblrRestClient, settings: Settings) -> int:
    spinner_name = random.choice(list(SPINNERS))  # noqa: S311
    progress = Progress(
        SpinnerColumn(spinner_name),
        *Progress.get_default_columns(),
        MofNCompleteColumn(),
        auto_refresh=False,
    )

    with Live(create_table(progress, "", [])) as live:
        for i in progress.track(range(settings.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr, settings)
                live.update(create_table(progress, *draft))
            except BaseException:  # noqa: BLE001
                # Stop the live so that everything gets printed under it.
                live.stop()
                Console().print_exception()
                return i

    return settings.generation.draft_count


def get_tumblr_client(settings: Settings) -> TumblrRestClient:
    tumblr = TumblrRestClient(
        settings.env.tumblr_consumer_key.get_secret_value(),
        settings.env.tumblr_consumer_secret.get_secret_value(),
        settings.env.tumblr_oauth_token.get_secret_value(),
        settings.env.tumblr_oauth_secret.get_secret_value(),
    )

    # Force pytumblr to return the raw Response object instead of a json.
    tumblr.request.json_parse = lambda response: response

    return tumblr


def main() -> None:
    settings = Settings()
    openai = OpenAI(api_key=settings.env.openai_api_key.get_secret_value())
    tumblr = get_tumblr_client(settings)

    num_drafts = create_drafts(openai, tumblr, settings)
    rich_print(f"[bold green]Generated {num_drafts} drafts! Check them out at:[/] https://tumblr.com/blog/{settings.env.blogname}/drafts")


if __name__ == "__main__":
    sys_exit(main())
