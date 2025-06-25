import rich

from src.tumblrbot import training
from src.tumblrbot.common import run_main
from src.tumblrbot.settings.config import CONFIG
from src.tumblrbot.settings.tokens import TOKENS
from src.tumblrbot.tumblr import download_posts


def main() -> None:
    post_paths = download_posts(
        TOKENS.tumblr_consumer_key,
        CONFIG.training.blognames,
        CONFIG.training.data_directory,
    )
    rich.print()
    training.main(post_paths)


run_main(__name__, main)
