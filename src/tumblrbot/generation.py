from random import random

import rich
from openai import OpenAI

from common import CustomLive, Tags, run_main
from src.tumblrbot.config import get_settings, get_tokens


def generate_tags(post_content: str, openai: OpenAI) -> Tags | None:
    if random() < get_settings.generation.tags_chance:  # noqa: S311
        response = openai.responses.parse(
            input=post_content,
            model=get_settings.model_name,
            text_format=Tags,
            instructions="Extract a very short list of the most important subjects from the provided text.",
        )

        return response.output_parsed

    return None


def generate_text(openai: OpenAI) -> str:
    response = openai.responses.create(
        input=get_settings.user_message,
        model=get_tokens.openai_model,
    )
    return response.output_text


def create_draft(openai: OpenAI, tumblr: TumblrRestClient) -> tuple[str, Tags | None]:
    body = generate_text(openai)
    tags = generate_tags(body, openai)

    response = tumblr.create_text(
        get_settings.generation.blogname,
        state="draft",
        tags=tags.tags if tags else [""],
        format="markdown",
        body=body,
    )
    response.raise_for_status()

    return body, tags


def create_drafts(openai: OpenAI, tumblr: TumblrRestClient) -> None:
    message = f"View drafts here: https://tumblr.com/blog/{get_settings.generation.blogname}/drafts"
    with CustomLive() as live:
        for i in live.progress.track(range(get_settings.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr)
                live.custom_update(*draft)
            except BaseException as exc:
                exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                raise

    rich.print(f":chart_increasing: [bold green]Generated {get_settings.generation.draft_count} draft(s).[/] {message}")


def get_tumblr_client() -> TumblrRestClient:
    tumblr = TumblrRestClient(
        get_tokens.tumblr_consumer_key,
        get_tokens.tumblr_consumer_secret.get_secret_value(),
        get_tokens.tumblr_oauth_token,
        get_tokens.tumblr_oauth_secret.get_secret_value(),
    )

    # Force pytumblr to return the raw Response object instead of a json.
    tumblr.request.json_parse = lambda response: response

    return tumblr


def main() -> None:
    openai = OpenAI(api_key=get_tokens.openai_api_key.get_secret_value())
    tumblr = get_tumblr_client()

    create_drafts(openai, tumblr)


run_main(__name__, main)
