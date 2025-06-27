import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install

from tumblrbot import generation, training
from tumblrbot.settings import TOKENS
from tumblrbot.tumblr import TumblrSession, write_tumblr_credentials
from tumblrbot.utils import print_prompt, token_prompt, yes_no_prompt


def main() -> None:
    if not all(TOKENS.tumblr.model_dump().values()) or yes_no_prompt("Reset Tumblr Tokens?"):
        write_tumblr_credentials()

    if not TOKENS.openai_api_key or yes_no_prompt("Reset OpenAI Tokens?"):
        print_prompt("https://platform.openai.com/settings/organization/api-keys", "API key")
        TOKENS.openai_api_key = token_prompt("API Key", secret=True)

    with TumblrSession() as session:
        should_download = yes_no_prompt("Download latest posts?")
        post_paths, total = session.write_all_published_posts(should_download=should_download)

        if yes_no_prompt("Create training data?"):
            training.main(post_paths, total)

        # TODO: add fine-tuning

        if yes_no_prompt("Generate drafts?"):
            generation.main(session)


if __name__ == "__main__":
    # It seems like calling 'python script.py' will use the relative path to the script.
    # Meanwhile, double-clicking or calling the script directly will use an absolute path to the script.
    # So, this is currently the only way we know to tell if the console window will close after running.
    # Not sure how reliable this is, especially across platforms, but it should work for now.
    console_auto_closes = Path(sys.argv[0]).is_absolute()

    try:
        install(show_locals=True)
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
