from functools import partial
from locale import LC_ALL, setlocale
from pathlib import Path
from shutil import rmtree
from sys import exit as sys_exit
from sys import maxsize
from typing import TYPE_CHECKING

from openai import OpenAI
from questionary import Choice, checkbox, select
from rich import print as rich_print
from rich.console import Console
from rich.traceback import install

from tumblrbot.flow.download import PostDownloader
from tumblrbot.flow.examples import ExamplesWriter
from tumblrbot.flow.fine_tune import FineTuner
from tumblrbot.flow.generate import DraftGenerator
from tumblrbot.utils.common import FlowClass
from tumblrbot.utils.models import Config, Tokens
from tumblrbot.utils.tumblr import TumblrSession

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from questionary.prompts.common import FormattedText


def main() -> None:
    install()
    setlocale(LC_ALL, "")

    console = Console()
    tokens = Tokens.load()

    with OpenAI(api_key=tokens.openai_api_key, max_retries=maxsize) as openai, TumblrSession(tokens) as tumblr:
        post_downloader = PostDownloader(openai, tumblr)
        examples_writer = ExamplesWriter(openai, tumblr)
        fine_tuner = FineTuner(openai, tumblr)
        draft_generator = DraftGenerator(openai, tumblr)

        while True:
            delete_choices = [
                create_delete_choice("Delete downloaded posts", "Delete all downloaded posts.", FlowClass.config.data_directory),
                create_delete_choice("Delete training data", "Delete generated training data.", FlowClass.config.examples_file),
            ]

            reset_choices = [
                create_delete_choice("Reset config settings", "Reset all settings, excluding tokens.", Config.get_toml_file()),
                create_delete_choice("Reset token settings", "Reset OpenAI and Tumblr tokens.", Tokens.get_toml_file()),
            ]

            choices = [
                Choice("Download latest posts", post_downloader.main, description="Download latest posts from blogs."),
                Choice("Create training data", examples_writer.main, description="Create training data file that can be used to fine-tune a model."),
                Choice("Filter training data", examples_writer.filter_examples, description="Remove training data flagged by OpenAI. May fix errors with fine-tuning validation."),
                Choice("Fine-tune model", fine_tuner.main, description="Resume monitoring the previous fine-tuning process." if FlowClass.config.job_id else "Upload data to OpenAI and start fine-tuning."),
                Choice("Generate drafts", draft_generator.main, description="Generate and upload posts to the bot's drafts."),
                create_submenu_choice("Delete saved data", delete_choices),
                create_submenu_choice("Reset settings", reset_choices, should_exit_on_success=True),
                Choice("Quit", sys_exit, description="Quit this program."),
            ]

            console.rule()
            if FlowClass.config.examples_file.exists():
                fine_tuner.print_estimates()
            else:
                console.print("[gray62]Hint: Try creating training data to see price estimates for fine-tuning.")

            for choice in checkbox(
                "Select action(s) and then press <enter>",
                choices,
                validate=lambda response: bool(response) or "Please select at least one action...",
            ).unsafe_ask():
                choice()


def create_submenu_choice(verb: str, choices: Sequence[str | Choice[Path] | dict[str, object]], *, should_exit_on_success: bool = False) -> Choice[partial[None]]:
    return Choice(
        f"> {verb}...",
        partial(
            create_submenu,
            choices,
            should_exit_on_success=should_exit_on_success,
        ),
        description=f"Open a submenu that lets you {verb.lower()}",
    )


def create_submenu(choices: Sequence[str | Choice[Path] | dict[str, object]], *, should_exit_on_success: bool) -> None:
    try:
        if response := checkbox("v Press <enter> without a selection to exit this menu", choices).unsafe_ask():
            for choice in response:
                rich_print(f"[gray62]Removing {choice}...")
                if choice.is_dir():
                    rmtree(choice)
                else:
                    choice.unlink()

            rich_print("[gray62]Completed!")

            if should_exit_on_success:
                rich_print("[bold blue]This program will now close!")
                sys_exit()
    except AttributeError:
        select("v Press <enter> to exit this menu", [*choices, "Return"]).unsafe_ask()


def create_delete_choice(title: FormattedText, description: str | None, path: Path) -> Choice[Path]:
    return Choice(
        title,
        path,
        None if path.exists() else "does not exist",
        description=description,
    )


if __name__ == "__main__":
    sys_exit(main())
