from locale import LC_ALL, setlocale
from sys import exit as sys_exit

from openai import OpenAI
from rich.prompt import Confirm
from rich.traceback import install

from tumblrbot.flow.download import PostDownloader
from tumblrbot.flow.examples import ExamplesWriter
from tumblrbot.flow.fine_tune import FineTuner
from tumblrbot.flow.generate import DraftGenerator
from tumblrbot.utils.common import FlowClass
from tumblrbot.utils.models import Tokens
from tumblrbot.utils.tumblr import TumblrSession


def main() -> None:
    setlocale(LC_ALL, "")

    install()

    tokens = Tokens.load()
    with OpenAI(api_key=tokens.openai_api_key) as openai, TumblrSession(tokens) as tumblr:
        if Confirm.ask("Download latest posts?", default=False):
            PostDownloader(openai, tumblr).main()

        examples_writer = ExamplesWriter(openai, tumblr)
        if Confirm.ask("Create training data?", default=False):
            examples_writer.main()

        if Confirm.ask("Remove training data flagged by the OpenAI moderation? [bold]This can sometimes resolve errors with fine-tuning validation, but is slow.", default=False):
            examples_writer.filter_examples()

        fine_tuner = FineTuner(openai, tumblr)
        fine_tuner.print_estimates()

        message = "Resume monitoring the previous fine-tuning process?" if FlowClass.config.job_id else "Upload data to OpenAI for fine-tuning?"
        if Confirm.ask(f"{message} [bold]You must do this to set the model to generate drafts from. Alternatively, manually enter a model into the config", default=False):
            fine_tuner.main()

        if Confirm.ask("Generate drafts?", default=False):
            DraftGenerator(openai, tumblr).main()


if __name__ == "__main__":
    sys_exit(main())
