from random import random

import rich

from tumblrbot.models import Post
from tumblrbot.utils import PreviewLive, UtilClass


class DraftGenerator(UtilClass):
    def generate_tags(self, content: Post.Block) -> Post | None:
        if random() < self.config.tags_chance:  # noqa: S311
            return self.openai.responses.parse(
                input=content.text,
                instructions="You are an advanced text summarization tool. You should extract a very short list of the most important subjects from the input.",
                model=self.config.base_model,
                text_format=Post,
            ).output_parsed

        return None

    def generate_content(self) -> Post.Block:
        content = self.openai.responses.create(
            input=self.config.user_input,
            instructions=self.config.developer_message,
            model=self.config.generation.fine_tuned_model,
        ).output_text

        return Post.Block(type="text", text=content)  # pyright: ignore[reportCallIssue]

    def generate_post(self) -> Post:
        content = self.generate_content()
        tags = self.generate_tags(content)

        return Post(  # pyright: ignore[reportCallIssue]
            tags=tags.tags if tags else [],
            content=[content],
        )

    def create_drafts(self) -> None:
        message = f"View drafts here: https://tumblr.com/blog/{self.config.generation.blog_name}/drafts"

        with PreviewLive() as live:
            for i in live.progress.track(range(self.config.generation.draft_count), description="Generating drafts..."):
                try:
                    post = self.generate_post()
                    self.tumblr.create_draft_post(self.config.generation.blog_name, post)
                    live.custom_update(post)
                except BaseException as exc:
                    exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                    raise

        rich.print(f":chart_increasing: [bold green]Generated {self.config.generation.draft_count} draft(s).[/] {message}")
