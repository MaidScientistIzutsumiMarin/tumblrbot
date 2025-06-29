import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.traceback import install

from tumblrbot import training
from tumblrbot.openai_utils import OpenAISession
from tumblrbot.settings import TOKENS
from tumblrbot.tumblr_utils import TumblrSession, write_tumblr_credentials
from tumblrbot.utils import token_prompt, yes_no_prompt


def main() -> None:
    if not all(TOKENS.tumblr.model_dump().values()):
        write_tumblr_credentials()

    if not TOKENS.openai_api_key:
        (TOKENS.openai_api_key,) = token_prompt("https://platform.openai.com/api-keys", "API key")
        TOKENS.model_post_init()

    with OpenAISession() as openai, TumblrSession() as tumblr:
        should_download = yes_no_prompt("Download latest posts?")
        post_paths = tumblr.write_all_published_posts(should_download=should_download)

        should_write = yes_no_prompt("Create training data?")
        tokens = training.main(post_paths, should_write=should_write)

        if yes_no_prompt("Upload data to OpenAI for fine-tuning?"):
            openai.start_fine_tuning(tokens)

        if yes_no_prompt("Generate drafts?"):
            openai.create_drafts(tumblr)


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
