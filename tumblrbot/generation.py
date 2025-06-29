import rich
from openai import OpenAI
from openai.types.responses import ParsedResponse

from tumblrbot.settings import CONFIG
from tumblrbot.tumblr import TumblrSession
from tumblrbot.utils import Post, PreviewLive


def generate_content(openai: OpenAI) -> ParsedResponse[Post]:
    return openai.responses.parse(
        input=CONFIG.user_input,
        model=CONFIG.generation.fine_tuned_model,
        text_format=Post,
        instructions=CONFIG.developer_message,
    )


def generate_tags(response_id: str, openai: OpenAI) -> Post | None:
    return openai.responses.parse(
        input="Extract the most important subjects.",
        model=CONFIG.base_model,
        text_format=Post,
        instructions="You are an advanced text summarization tool. You return the requested data to the user.",
        previous_response_id=response_id,
    ).output_parsed


def generate_post(openai: OpenAI) -> Post | None:
    response = generate_content(openai)
    if response.output_parsed and (tags := generate_tags(response.id, openai)):
        response.output_parsed.tags = tags.tags
    return response.output_parsed


def main(openai: OpenAI, tumblr: TumblrSession) -> None:
    message = f"View drafts here: https://tumblr.com/blog/{CONFIG.generation.blog_name}/drafts"

    with PreviewLive() as live:
        for i in live.progress.track(range(CONFIG.generation.draft_count), description="Generating drafts..."):
            try:
                if post := generate_post(openai):
                    tumblr.create_draft_post(post)
                    live.custom_update(post)
            except BaseException as exc:
                exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                raise

    rich.print(f":chart_increasing: [bold green]Generated {CONFIG.generation.draft_count} draft(s).[/] {message}")
