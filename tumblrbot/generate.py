from random import random

import rich

from tumblrbot.tumblr import Post
from tumblrbot.utils import PreviewLive, PreviewUtil


class DraftGenerator(PreviewUtil):
    def generate_tags(self, content: Post.ContentBlock) -> Post | None:
        if random() < self.config.tags_chance:
            return self.openai.responses.parse(
                input=content.text,
                instructions="You are an advanced text summarization tool. You should extract a very short list of the most important subjects.",
                model=self.config.base_model,
                text_format=Post,
            ).output_parsed

        return None

    def generate_content(self) -> Post.ContentBlock:
        content = self.openai.responses.create(
            input=self.config.user_input,
            instructions=self.config.developer_message,
            model=self.config.generation.fine_tuned_model,
        ).output_text
        return Post.ContentBlock(
            type="text",
            text=content,
        )

    def generate_post(self) -> Post:
        content = self.generate_content()
        post = Post(content=[content])

        if tags := self.generate_tags(content):
            post.tags = tags.tags
        return post

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
