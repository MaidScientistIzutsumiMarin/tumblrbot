import rich

import training
from common import run_main
from confiig import CONFIG
from tokens import TOKENS
from tumblr import download_posts


def main() -> None:
    post_paths = download_posts(
        TOKENS.tumblr_consumer_key,
        CONFIG.training.blognames,
        CONFIG.training.data_directory,
    )
    rich.print()
    training.main(post_paths)


run_main(__name__, main)
