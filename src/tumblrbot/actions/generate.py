from dataclasses import dataclass
from functools import cache
from random import choice, random, sample
from typing import TYPE_CHECKING, override

from openai import BadRequestError
from rich import print as rich_print

from tumblrbot.actions.base import BaseAction
from tumblrbot.utils.common import PreviewLive, config, localize_number
from tumblrbot.utils.models import Block, Post

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class DraftGenerator(BaseAction):
    @override
    def main(self) -> None:
        message = f"View drafts here: https://tumblr.com/blog/{config.upload_blog_identifier}/drafts"

        with PreviewLive() as live:
            for i in live.progress.track(range(config.draft_count), description="Generating drafts..."):
                try:
                    post = self.generate_post()
                    self.tumblr.create_post(config.upload_blog_identifier, post)
                    live.custom_update(post)
                except BadRequestError as e:
                    e.add_note("[italic]Hint: Try fine-tuning a model or changing the fine-tuned model value in the config...")
                    raise
                except BaseException as e:
                    if i > 0:
                        e.add_note(f"📉 An error occurred! Generated {localize_number(i)} draft(s) before failing. {message}")
                    raise

        rich_print(f":chart_increasing: [bold green]Generated {localize_number(config.draft_count)} draft(s).[/] {message}")

    def generate_post(self) -> Post:
        if original := self.get_random_post():
            user_message = config.reblog_user_message.format(original)
            if "{}" not in config.reblog_user_message:
                user_message += str(original)
        else:
            original = Post()
            user_message = config.user_message
        text = self.generate_text(user_message)

        if tags := self.generate_tags(text):
            tags = tags.tags

        return Post(
            content=[Block(text=text)],
            tags=tags or [],
            parent_tumblelog_uuid=original.blog.uuid,
            parent_post_id=original.id,
            reblog_key=original.reblog_key,
        )

    def generate_text(self, user_message: str) -> str:
        return self.openai.responses.create(
            input=user_message,
            instructions=config.developer_message,
            model=config.fine_tuned_model,
        ).output_text

    def generate_tags(self, text: str) -> Post | None:
        if random() < config.tags_chance:  # noqa: S311
            return self.openai.responses.parse(
                text_format=Post,
                input=text,
                instructions=config.tags_developer_message,
                model=config.base_model,
            ).output_parsed

        return None

    def get_random_post(self) -> Post | None:
        if config.reblog_blog_identifiers and random() < config.reblog_chance:  # noqa: S311
            blog_identifier = choice(config.reblog_blog_identifiers)  # noqa: S311
            for offset in self.get_offsets(blog_identifier):
                for raw_post in self.tumblr.retrieve_published_posts(
                    blog_identifier,
                    offset,
                ).response.posts:
                    post = Post.model_validate(raw_post)
                    if post.valid_text_post() and self.is_trail_valid(post.trail):
                        return post

        return None

    @cache  # noqa: B019 # This creates a memory leak, but it doesn't matter since this class isn't discarded until the end of the program anyways.
    def get_offsets(self, blog_identifier: str) -> Iterable[int]:
        total = self.tumblr.retrieve_blog_info(blog_identifier).response.blog.posts
        # The same Iterable object is cached, so reading an element will effectively discard it. This prevents checking the same offsets twice.
        return iter(sample(range(total), total))

    def is_trail_valid(self, trail: list[Post]) -> bool:
        # Checks if every post in the reblog trail is valid and that the blog that created the post is in the allowed reblog list.
        return all(post.valid_text_post() and post.blog.name in config.reblog_blog_identifiers for post in trail)
