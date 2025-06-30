import sys
from collections.abc import Generator
from pathlib import Path

import rich
from openai import DefaultHttpxClient, OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install

from tumblrbot.download import PostDownloader
from tumblrbot.examples import ExamplesWriter
from tumblrbot.fine_tune import FineTuner
from tumblrbot.generate import DraftGenerator
from tumblrbot.settings import Tokens
from tumblrbot.tumblr import TumblrClient
from tumblrbot.utils import yes_no_prompt


def token_prompt(url: object, *tokens: object) -> Generator[str]:
    token_strings = [f"[cyan]{token}[/]" for token in tokens]
    url_prompt_tokens = " and ".join(token_strings)

    rich.print(f"Retrieve your {url_prompt_tokens} from: {url}")
    for token in token_strings:
        prompt = f"Enter your [cyan]{token}"
        yield Prompt.ask(prompt).strip()

    rich.print()


def main() -> None:
    # It seems like calling 'python script.py' will use the relative path to the script.
    # Meanwhile, double-clicking or calling the script directly will use an absolute path to the script.
    # So, this is currently the only way we know to tell if the console window will close after running.
    # Not sure how reliable this is, especially across platforms, but it should work for now.
    console_auto_closes = Path(sys.argv[0]).is_absolute()

    try:
        install(show_locals=True)

        tokens = Tokens()
        if tokens.any_values_missing():
            (tokens.openai_api_key,) = token_prompt("https://platform.openai.com/api-keys", "API key")
            tokens.model_post_init()

        if tokens.tumblr.any_values_missing():
            tokens.tumblr.client_id, tokens.tumblr.client_secret = token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")
            tokens.model_post_init()

        with (
            OpenAI(
                api_key=tokens.openai_api_key,
                http_client=DefaultHttpxClient(http2=True),
            ) as openai,
            TumblrClient(tokens) as tumblr,
        ):
            post_downloader = PostDownloader(openai, tumblr)
            if yes_no_prompt("Download latest posts?"):
                post_downloader.download()
            download_paths = post_downloader.get_download_paths()

            examples_writer = ExamplesWriter(openai, tumblr, download_paths)
            if yes_no_prompt("Create training data?"):
                examples_writer.write_examples()
            estimated_tokens = sum(examples_writer.count_tokens())

            fine_tuner = FineTuner(openai, tumblr, estimated_tokens)
            fine_tuner.print_estimates()
            if yes_no_prompt("Upload data to OpenAI for fine-tuning?"):
                fine_tuner.fine_tune()

            if yes_no_prompt("Generate drafts?"):
                DraftGenerator(openai, tumblr).create_drafts()
    except BaseException:
        if console_auto_closes:
            Console(stderr=True, style="logging.level.error").print_exception()
        raise
    finally:
        if console_auto_closes:
            Prompt.ask("Press Enter to close")


if __name__ == "__main__":
    sys.exit(main())
