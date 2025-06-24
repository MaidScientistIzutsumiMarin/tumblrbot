from random import random

import rich
from openai import OpenAI
from pytumblr import TumblrRestClient

from common import CustomLive, run_main
from settings import ENV, SETTINGS


def generate_tags(post_content: str, openai: OpenAI) -> set[str]:
    if random() > SETTINGS.generation.tags_chance:  # noqa: S311
        return {""}

    response = openai.responses.create(
        input=f"Extract the most important subjects from the following text:\n\n{post_content}",
        model=SETTINGS.model_name,
        instructions="You are an advanced text summarization tool. You return the requested data to the user as a list of comma separated strings.",
    )

    # Extracting the text from the model's response and splitting into a list of strings.
    # It's not technically necessary to split here since Tumblr will handle it for us,
    # but it makes previewing the tags much simpler and consistent.
    tags = response.output_text.split(",")
    return set(map(str.strip, tags))


def generate_text(openai: OpenAI) -> str:
    response = openai.responses.create(
        input=SETTINGS.user_message,
        model=ENV.openai_model.get_secret_value(),
        instructions=SETTINGS.developer_message,
    )
    return response.output_text


def create_draft(openai: OpenAI, tumblr: TumblrRestClient) -> tuple[str, set[str]]:
    body = generate_text(openai)
    tags = generate_tags(body, openai)

    response = tumblr.create_text(
        SETTINGS.generation.blogname,
        state="draft",
        tags=tags,
        format="markdown",
        body=body,
    )
    response.raise_for_status()

    return body, tags


def create_drafts(openai: OpenAI, tumblr: TumblrRestClient) -> None:
    message = f"View drafts here: https://tumblr.com/blog/{SETTINGS.generation.blogname}/drafts"
    with CustomLive() as live:
        for i in live.progress.track(range(SETTINGS.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr)
                live.custom_update(*draft)
            except BaseException as exc:
                exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                raise

    rich.print(f":chart_increasing: [bold green]Generated {SETTINGS.generation.draft_count} draft(s).[/] {message}")


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
    openai = OpenAI(api_key=ENV.openai_api_key.get_secret_value())
    tumblr = get_tumblr_client()

    create_drafts(openai, tumblr)


run_main(__name__, main)
