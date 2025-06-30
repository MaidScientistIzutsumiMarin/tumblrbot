import sys
from collections.abc import Generator
from pathlib import Path

import rich
from authlib.integrations.httpx_client import OAuth2Client
from openai import OpenAI
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


def token_prompt(url: str, *tokens: str) -> Generator[str]:
    token_strings = [f"[cyan]{token}[/]" for token in tokens]
    url_prompt_tokens = " and ".join(token_strings)

    rich.print(f"Retrieve your {url_prompt_tokens} from: {url}")
    for token in token_strings:
        prompt = f"Enter your [cyan]{token}"
        yield Prompt.ask(prompt).strip()

    rich.print()


def verify_tokens() -> Tokens:
    tokens = Tokens()

    if not tokens.openai_api_key:
        (tokens.openai_api_key,) = token_prompt("https://platform.openai.com/api-keys", "API key")
        tokens.model_post_init()

    if not (tokens.tumblr.client_id and tokens.tumblr.client_secret):
        tokens.tumblr.client_id, tokens.tumblr.client_secret = token_prompt("https://tumblr.com/oauth/apps", "consumer key", "consumer secret")
        tokens.model_post_init()

    if not tokens.tumblr.token:
        with OAuth2Client(
            tokens.tumblr.client_id,
            tokens.tumblr.client_secret,
            scope="basic write offline_access",
        ) as client:
            uri, _ = client.create_authorization_url("https://tumblr.com/oauth2/authorize")
            authorization_response = token_prompt(uri, "full redirected URL")
            tokens.tumblr.token = client.fetch_token("https://api.tumblr.com/v2/oauth2/token", authorization_response=authorization_response)
            tokens.model_post_init()

    return tokens


def main() -> None:
    # It seems like calling 'python script.py' will use the relative path to the script.
    # Meanwhile, double-clicking or calling the script directly will use an absolute path to the script.
    # So, this is currently the only way we know to tell if the console window will close after running.
    # Not sure how reliable this is, especially across platforms, but it should work for now.
    console_auto_closes = Path(sys.argv[0]).is_absolute()

    try:
        install(show_locals=True)
        tokens = verify_tokens()

        with OpenAI(api_key=tokens.openai_api_key) as openai, TumblrClient(tokens) as tumblr:
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
                DraftGenerator(openai=openai, tumblr=tumblr).create_drafts()
    except BaseException:
        if console_auto_closes:
            Console(stderr=True, style="logging.level.error").print_exception()
        raise
    finally:
        if console_auto_closes:
            Prompt.ask("Press Enter to close")


if __name__ == "__main__":
    sys.exit(main())
