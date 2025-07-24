from random import random
from typing import override

import rich
from rich.prompt import IntPrompt

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Post


class DraftGenerator(FlowClass):
    @override
    def main(self) -> None:
        self.config.draft_count = IntPrompt.ask("How many drafts should be generated?", default=self.config.draft_count)

        message = f"View drafts here: https://tumblr.com/blog/{self.config.upload_blog_identifier}/drafts"

        with PreviewLive() as live:
            for i in live.progress.track(range(self.config.draft_count), description="Generating drafts..."):
                try:
                    post = self.generate_post()
                    self.tumblr.create_post(self.config.upload_blog_identifier, post)
                    live.custom_update(post)
                except BaseException as exception:
                    exception.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                    raise

        rich.print(f":chart_increasing: [bold green]Generated {self.config.draft_count} draft(s).[/] {message}")

    def generate_post(self) -> Post:
        text = self.generate_text()
        if tags := self.generate_tags(text):
            tags = tags.tags
        return Post(
            content=[Post.Block(type="text", text=text)],
            tags=tags or [],
            state="draft",
        )

    def generate_text(self) -> str:
        return self.openai.responses.create(
            input=self.config.user_message,
            instructions=self.config.developer_message,
            model=self.config.fine_tuned_model,
        ).output_text

    def generate_tags(self, text: str) -> Post | None:
        if random() < self.config.tags_chance:  # noqa: S311
            return self.openai.responses.parse(
                text_format=Post,
                input=text,
                instructions=self.config.tags_developer_message,
                model=self.config.base_model,
            ).output_parsed

        return None
