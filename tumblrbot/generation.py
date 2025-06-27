from random import random

import rich
from openai import OpenAI

from tumblrbot.settings import CONFIG, TOKENS
from tumblrbot.tumblr import TumblrSession
from tumblrbot.utils import PreviewLive


def generate_tags(post_content: str, openai: OpenAI) -> Tags | None:
    if random() < CONFIG.generation.tags_chance:  # noqa: S311
        response = openai.responses.parse(
            input=post_content,
            model=CONFIG.model_name,
            text_format=Tags,
            instructions="Extract a very short list of the most important subjects from the provided text.",
        )

        return response.output_parsed

    return None


def generate_text(openai: OpenAI) -> str:
    response = openai.responses.create(
        input=CONFIG.user_message,
        model=CONFIG.generation.openai_model,
    )
    return response.output_text


def create_draft(openai: OpenAI, tumblr: TumblrSession) -> tuple[str, Tags | None]:
    body = generate_text(openai)
    tags = generate_tags(body, openai)

    response = tumblr.create_draft_post(
        CONFIG.generation.blogname,
        tags=tags.tags if tags else "",
    )
    response.raise_for_status()

    return body, tags


def create_drafts(openai: OpenAI, tumblr: TumblrSession) -> None:
    message = f"View drafts here: https://tumblr.com/blog/{CONFIG.generation.blogname}/drafts"
    with PreviewLive() as live:
        for i in live.progress.track(range(CONFIG.generation.draft_count), description="Generating drafts..."):
            try:
                draft = create_draft(openai, tumblr)
                live.custom_update(*draft)
            except BaseException as exc:
                exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                raise

    rich.print(f":chart_increasing: [bold green]Generated {CONFIG.generation.draft_count} draft(s).[/] {message}")


def main() -> None:
    openai = OpenAI(api_key=TOKENS.openai_api_key.get_secret_value())
    tumblr = TumblrSession()

    create_drafts(openai, tumblr)
