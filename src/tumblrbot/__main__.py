from locale import LC_ALL, setlocale
from sys import exit as sys_exit
from sys import maxsize

from openai import OpenAI
from questionary import Choice, checkbox
from rich.console import Console
from rich.traceback import install

from tumblrbot.flow.download import PostDownloader
from tumblrbot.flow.examples import ExamplesWriter
from tumblrbot.flow.fine_tune import FineTuner
from tumblrbot.flow.generate import DraftGenerator
from tumblrbot.utils.common import FlowClass
from tumblrbot.utils.models import Tokens
from tumblrbot.utils.tumblr import TumblrSession


def main() -> None:
    install()
    setlocale(LC_ALL, "")

    install()

    console = Console()

    tokens = Tokens.load()
    with OpenAI(api_key=tokens.openai_api_key, max_retries=maxsize) as openai, TumblrSession(tokens) as tumblr:
        post_downloader = PostDownloader(openai, tumblr)
        examples_writer = ExamplesWriter(openai, tumblr)
        fine_tuner = FineTuner(openai, tumblr)
        draft_generator = DraftGenerator(openai, tumblr)

        while True:
            action_choices = [
                Choice("Download latest posts", post_downloader.main, description=""),
                Choice("Create training data", examples_writer.main, description=""),
                Choice("Filter training data", examples_writer.filter_examples, description="Removes training data flagged by the OpenAI moderation. This can sometimes resolve errors with fine-tuning validation, but is slow."),
                Choice("Fine-tune model", fine_tuner.main, description="Resume monitoring the previous fine-tuning process?" if FlowClass.config.job_id else "Upload data to OpenAI for fine-tuning? You must do this to set the model to generate drafts from. Alternatively, manually enter a model into the config."),
                Choice("Generate drafts", draft_generator.main, description=""),
                Choice("Quit", sys_exit, description="Quit this program."),
            ]

            for action in checkbox("Select an action", action_choices).ask():
                action()
            console.rule()
            fine_tuner.print_estimates()


if __name__ == "__main__":
    sys_exit(main())
