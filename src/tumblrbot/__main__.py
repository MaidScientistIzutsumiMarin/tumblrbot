from openai import DefaultHttpxClient, OpenAI
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
    with (
        OpenAI(api_key=tokens.openai_api_key.get_secret_value(), http_client=DefaultHttpxClient(http2=True)) as openai,
        TumblrSession(tokens=tokens) as tumblr,
    ):
        post_downloader = PostDownloader(openai, tumblr)
        if Confirm.ask("Download latest posts?", default=False):
            post_downloader.download()
        download_paths = post_downloader.get_data_paths()

        examples_writer = ExamplesWriter(openai, tumblr, download_paths)
        if Confirm.ask("Create training data?", default=False):
            examples_writer.write_examples()
        estimated_tokens = sum(examples_writer.count_tokens())

        fine_tuner = FineTuner(openai, tumblr, estimated_tokens)
        fine_tuner.print_estimates()

        message = "Resume monitoring the previous fine-tuning process?" if FlowClass.config.job_id else "Upload data to OpenAI for fine-tuning?"
        if Confirm.ask(f"{message} [bold]You must do this to set the model to generate drafts from. Alternatively, manually enter a model into the config", default=False):
            fine_tuner.fine_tune()

        if Confirm.ask("Generate drafts?", default=False):
            DraftGenerator(openai, tumblr).create_drafts()
