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
    install()

    tokens = Tokens.read_from_keyring()
    with OpenAI(api_key=tokens.openai_api_key) as openai, TumblrSession(tokens) as tumblr:
        if Confirm.ask("Download latest posts?", default=False):
            PostDownloader(openai=openai, tumblr=tumblr).main()

        if Confirm.ask("Create training data?", default=False):
            ExamplesWriter(openai=openai, tumblr=tumblr).main()

        fine_tuner = FineTuner(openai=openai, tumblr=tumblr)
        fine_tuner.print_estimates()

        message = "Resume monitoring the previous fine-tuning process?" if FlowClass.config.job_id else "Upload data to OpenAI for fine-tuning?"
        if Confirm.ask(f"{message} [bold]You must do this to set the model to generate drafts from. Alternatively, manually enter a model into the config", default=False):
            fine_tuner.main()

        if Confirm.ask("Generate drafts?", default=False):
            DraftGenerator(openai=openai, tumblr=tumblr).main()
