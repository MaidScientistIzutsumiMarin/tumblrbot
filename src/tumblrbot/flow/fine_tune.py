from datetime import datetime
from locale import currency, localeconv
from textwrap import dedent
from time import sleep
from typing import TYPE_CHECKING, override

from currency_converter import CurrencyConverter
from rich import print as rich_print
from rich.console import Console
from rich.progress import open as progress_open
from rich.prompt import Confirm
from tiktoken import encoding_for_model, get_encoding

from tumblrbot.utils.common import FlowClass, PreviewLive, localize_number
from tumblrbot.utils.models import Example

if TYPE_CHECKING:
    from collections.abc import Generator

    from openai.types.fine_tuning import FineTuningJob


class FineTuner(FlowClass):
    @staticmethod
    def dedent_print(text: str) -> None:
        rich_print(dedent(text).lstrip())

    @override
    def main(self) -> None:
        job = self.create_job()

        self.dedent_print(f"""
            [bold]Fine-tuning is starting...[/]
            View it online at: https://platform.openai.com/finetune/{job.id}
                Created at: {datetime.fromtimestamp(job.created_at)}
                Base Model: {job.model}

            [italic dim]Closing this terminal will not stop the fine-tuning. This will take a while...\
        """)  # noqa: DTZ006

        with PreviewLive() as live:
            task_id = live.progress.add_task("", total=None)

            while job.status in {"validating_files", "queued", "running"}:
                job = self.poll_job_status()

                live.progress.update(
                    task_id,
                    description=f"Fine-tuning: [italic]{job.status.replace('_', ' ').title()}[/]...",
                )

                sleep(1)

        self.process_completed_job(job)

    def create_job(self) -> FineTuningJob:
        if self.config.job_id:
            return self.poll_job_status()

        with progress_open(self.config.examples_file, "rb", description=f"Uploading [purple]{self.config.examples_file}[/]...") as fp:
            file = self.openai.files.create(
                file=fp,
                purpose="fine-tune",
            )
        rich_print()

        job = self.openai.fine_tuning.jobs.create(
            model=self.config.base_model,
            training_file=file.id,
        )

        self.config.job_id = job.id
        return job

    def poll_job_status(self) -> FineTuningJob:
        job = self.openai.fine_tuning.jobs.retrieve(self.config.job_id)

        if self.config.expected_epochs != job.hyperparameters.n_epochs and isinstance(job.hyperparameters.n_epochs, int):
            self.config.expected_epochs = job.hyperparameters.n_epochs

            self.dedent_print(f"""
                The number of epochs has been updated to {job.hyperparameters.n_epochs}!
                [cyan]Updated the config.
            """)
            self.print_estimates()

        return job

    def process_completed_job(self, job: FineTuningJob) -> None:
        if job.trained_tokens is not None:
            self.dedent_print(f"""
                Trained Tokens: {localize_number(job.trained_tokens):,}
                Cost: {self.get_cost_string(job.trained_tokens)}
            """)

        self.config.job_id = ""

        if job.status != "succeeded":
            if Confirm.ask("[gray62]Delete uploaded examples file?", default=False):
                self.openai.files.delete(job.training_file)
                rich_print()

            if job.status == "failed" and job.error is not None:
                raise RuntimeError(job.error.message)

        if job.fine_tuned_model is not None:
            self.config.fine_tuned_model = job.fine_tuned_model

    def print_estimates(self) -> None:
        estimated_tokens = sum(self.count_tokens())
        total_tokens = self.config.expected_epochs * estimated_tokens
        cost_string = self.get_cost_string(total_tokens)

        self.dedent_print(f"""
            Tokens: {localize_number(estimated_tokens)}:
            Total tokens for [bold orange1]{self.config.expected_epochs}[/] epoch(s): {localize_number(total_tokens)}
            Expected cost when trained with [bold purple]{self.config.base_model}[/]: {cost_string}
            NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                    [italic red]Amelia, Mutsumi, and Marin are not responsible for any inaccuracies in the token count or estimated price.[/]
        """)

    def count_tokens(self) -> Generator[int]:
        # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
        # and https://cookbook.openai.com/examples/chat_finetuning_data_prep
        try:
            encoding = encoding_for_model(self.config.base_model)
        except KeyError as error:
            encoding = get_encoding("o200k_base")
            Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {''.join(error.args)}\n")

        with self.config.examples_file.open(encoding="utf_8") as fp:
            for line in fp:
                example = Example.model_validate_json(line)
                yield len(encoding.encode("assistant"))  # every reply is primed with <|start|>assistant<|message|>
                for message in example.messages:
                    yield 4 + len(encoding.encode(message.content))

    def get_cost_string(self, total_tokens: int) -> str:
        c = CurrencyConverter()
        cost = c.convert(self.config.token_price / 1000000 * total_tokens, "USD", localeconv()["int_curr_symbol"])
        return currency(cost, grouping=True)
