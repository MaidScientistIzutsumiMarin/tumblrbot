import sys
from collections.abc import Generator
from pathlib import Path

import rich
from openai import OpenAI
from pydantic import Secret
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.traceback import install

from tumblrbot.flow.download import PostDownloader
from tumblrbot.flow.examples import ExamplesWriter
from tumblrbot.flow.fine_tune import FineTuner
from tumblrbot.flow.generate import DraftGenerator
from tumblrbot.utils.settings import Tokens
from tumblrbot.utils.tumblr import TumblrClient


def start_flow(openai: OpenAI, tumblr: TumblrClient) -> None:
    post_downloader = PostDownloader(openai, tumblr)
    if Confirm.ask("Download latest posts?", default=False):
        post_downloader.download()
    download_paths = post_downloader.get_download_paths()

    examples_writer = ExamplesWriter(openai, tumblr, download_paths)
    if Confirm.ask("Create training data?", default=False):
        examples_writer.write_examples()
    estimated_tokens = sum(examples_writer.count_tokens())

    fine_tuner = FineTuner(openai, tumblr, estimated_tokens)
    fine_tuner.print_estimates()
    if Confirm.ask("Upload data to OpenAI for fine-tuning?", default=False):
        fine_tuner.fine_tune()

    if Confirm.ask("Generate drafts?", default=False):
        DraftGenerator(openai=openai, tumblr=tumblr).create_drafts()


def online_token_prompt(url: str, *tokens: str) -> Generator[Secret[str]]:
    token_strings = [f"[cyan]{token}[/]" for token in tokens]
    url_prompt_tokens = " and ".join(token_strings)

    rich.print(f"Retrieve your {url_prompt_tokens} from: {url}")
    for token in token_strings:
        prompt = f"Enter your {token} [yellow](hidden)"
        yield Secret(Prompt.ask(prompt, password=True).strip())

    rich.print()


def verify_tokens() -> Tokens:
    tokens = Tokens()

    if not tokens.openai.api_key.get_secret_value():
        (tokens.openai.api_key,) = online_token_prompt("https://platform.openai.com/api-keys", "API key")
        tokens.model_post_init()

    if not (tokens.tumblr.client_id.get_secret_value() and tokens.tumblr.client_secret.get_secret_value()):
        tokens.tumblr.client_id, tokens.tumblr.client_secret = online_token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")
        tokens.model_post_init()

    return tokens


def main() -> None:
    install(show_locals=True)
    tokens = verify_tokens()
    with OpenAI(api_key=tokens.openai.api_key.get_secret_value()) as openai, TumblrClient(tokens) as tumblr:
        start_flow(openai, tumblr)


if __name__ == "__main__":
    # It seems like calling 'python script.py' will use the relative path to the script.
    # Meanwhile, double-clicking or calling the script directly will use an absolute path to the script.
    # So, this is currently the only way we know to tell if the console window will close after running.
    # Not sure how reliable this is, especially across platforms, but it should work for now.
    console_auto_closes = Path(sys.argv[0]).is_absolute()

    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        if console_auto_closes:
            Console(stderr=True, style="logging.level.error").print_exception()
        raise
    finally:
        if console_auto_closes:
            Prompt.ask("Press Enter to close")
