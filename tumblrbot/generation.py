import rich
from openai import OpenAI

from tumblrbot.settings import CONFIG
from tumblrbot.tumblr import TumblrSession
from tumblrbot.utils import Post, PreviewLive


def generate_post(openai: OpenAI) -> Post | None:
    response = openai.responses.parse(
        input=CONFIG.user_message,
        model=CONFIG.generation.fine_tuned_model,
        text_format=Post,
    )
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
