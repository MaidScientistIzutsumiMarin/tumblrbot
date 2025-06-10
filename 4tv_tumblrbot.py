import random
from collections.abc import Iterable

from openai import OpenAI
from pytumblr import TumblrRestClient
from requests import Response
from rich import print as rich_print
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress
from rich.table import Table
from rich.traceback import install

from settings import Settings, start


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
        model=settings.env.openai_model,
        instructions=settings.user_message,
        max_output_tokens=4096 - len(settings.user_message.split()),
    )
    return response.output_text


def create_text(body: str, tags: list[str], tumblr: TumblrRestClient, settings: Settings) -> None:
    response = tumblr.create_text(  # type: ignore[reportUnknownMemberType]
        settings.env.blogname,
        state="draft",
        body=body,
        tags=tags or [""],
    )

    if "meta" in response and response["meta"]["status"] != 200:  # noqa: PLR2004
        host = tumblr.request.host  # type: ignore[reportUnknownMemberType]
        response_obj = Response()
        response_obj.status_code = response["meta"]["status"]
        response_obj.reason = response["meta"]["msg"]
        response_obj.url = f"{host}/v2/blog/{settings.env.blogname}/post"
        response_obj.raise_for_status()


def create_draft(openai: OpenAI, tumblr: TumblrRestClient, settings: Settings) -> tuple[str, list[str]]:
    body = generate_text(openai, settings)
    tags = generate_tags(body, openai, settings)
    create_text(body, tags, tumblr, settings)

    return body, tags


def create_table(progress: Progress, body: str, tags: Iterable[str]) -> Table:
    tags_string = " ".join(f"#{tag}" for tag in tags)

    table = Table.grid()
    table.add_row(progress)
    table.add_row(Panel.fit(body, title="Preview", subtitle=tags_string, subtitle_align="left"))
    return table


def main(settings: Settings) -> None:
    install()

    draft_url_text = f"Check them out at: https://tumblr.com/blog/{settings.env.blogname}/drafts"

    openai = OpenAI(api_key=settings.env.openai_api_key)
    tumblr = TumblrRestClient(
        settings.env.tumblr_consumer_key,
        settings.env.tumblr_consumer_secret,
        settings.env.tumblr_oauth_token,
        settings.env.tumblr_oauth_secret,
    )

    progress = Progress(*Progress.get_default_columns(), MofNCompleteColumn(), auto_refresh=False)
    with Live("", auto_refresh=False) as live:
        for i in progress.track(range(settings.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr, settings)
                live.update(create_table(progress, *draft), refresh=True)
            except BaseException as exc:
                msg = f"📉 An error occurred! Generated {i} drafts. {draft_url_text}"
                raise RuntimeError(msg) from exc

    rich_print(f":chart_increasing: [bold green]Successfully generated drafts![/] {draft_url_text}")


start(__name__, main)
