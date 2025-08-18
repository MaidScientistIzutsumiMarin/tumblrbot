from collections.abc import Iterable
from functools import cache
from random import choice, random, sample
from typing import override

import rich
from pydantic import ConfigDict
from rich.prompt import IntPrompt

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Post


class DraftGenerator(FlowClass):
    model_config = ConfigDict(frozen=True)  # Makes this class hashable.

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
        if original := self.get_random_post():
            user_message = f"{self.config.reblog_user_message}\n\n{original.get_content_text()}"
        else:
            original = Post()
            user_message = self.config.user_message
        text = self.generate_text(user_message)

        if tags := self.generate_tags(text):
            tags = tags.tags

        return Post(
            content=[Post.Block(type="text", text=text)],
            tags=tags or [],
            state="draft",
            parent_tumblelog_uuid=original.blog.uuid,
            parent_post_id=original.id,
            reblog_key=original.reblog_key,
        )

    def generate_text(self, user_message: str) -> str:
        return self.openai.responses.create(
            input=user_message,
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

    def get_random_post(self) -> Post | None:
        if self.config.reblog_blog_identifiers and random() < self.config.reblog_chance:  # noqa: S311
            blog_identifier = choice(self.config.reblog_blog_identifiers)  # noqa: S311
            for offset in self.get_offsets(blog_identifier):
                for raw_post in self.tumblr.retrieve_published_posts(
                    blog_identifier,
                    offset,
                ).response.posts:
                    post = Post.model_validate(raw_post)
                    if post.valid_text_post():
                        return post

        return None

    @cache  # noqa: B019 # This creates a memory leak, but it doesn't matter since this class isn't discarded until the end of the program anyways.
    def get_offsets(self, blog_identifier: str) -> Iterable[int]:
        total = self.tumblr.retrieve_blog_info(blog_identifier).response.blog.posts
        # The same Iterable object is cached, so reading an element will effectively discard it. This prevents checking the same offsets twice.
        return iter(sample(range(total), total))
