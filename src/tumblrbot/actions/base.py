from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai import OpenAI  # noqa: TC002

from tumblrbot.utils.common import config
from tumblrbot.utils.tumblr import TumblrSession  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class BaseAction:
    openai: OpenAI
    tumblr: TumblrSession

    @abstractmethod
    def main(self) -> None: ...

    def get_data_paths(self) -> list[Path]:
        return list(map(self.get_data_path, config.download_blog_identifiers))

    def get_data_path(self, blog_identifier: str) -> Path:
        return (config.data_directory / blog_identifier).with_suffix(".jsonl")
