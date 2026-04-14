from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from openai import OpenAI  # noqa: TC002

from tumblrbot.utils.models import Config
from tumblrbot.utils.tumblr import TumblrSession  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class BaseStep:
    config: ClassVar = Config.load()

    openai: OpenAI
    tumblr: TumblrSession

    @abstractmethod
    def main(self) -> None: ...

    def get_data_paths(self) -> list[Path]:
        return list(map(self.get_data_path, self.config.download_blog_identifiers))

    def get_data_path(self, blog_identifier: str) -> Path:
        return (self.config.data_directory / blog_identifier).with_suffix(".jsonl")
