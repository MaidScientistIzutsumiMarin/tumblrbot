from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from time import sleep

import rich
from openai import BadRequestError
from openai.types import FileObject
from openai.types.fine_tuning import FineTuningJob
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed, wait_random

from tumblrbot.utils.common import FlowClass, PreviewLive


@dataclass
class FineTuner(FlowClass):
    estimated_tokens: int

    @staticmethod
    def dedent_print(text: str) -> None:
        rich.print(dedent(text).lstrip())

    def process_completed_job(self, job: FineTuningJob) -> None:
        if job.trained_tokens is not None:
            self.dedent_print(f"""
                Trained Tokens: {job.trained_tokens:,}
                Cost: {self.get_cost_string(job.trained_tokens)}
            """)

        self.config.job_id = ""

        if job.status == "failed" and job.error is not None:
            raise RuntimeError(job.error.message)

        if job.fine_tuned_model:
            self.config.fine_tuned_model = job.fine_tuned_model or ""

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

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(1.5) + wait_random(),
        retry=retry_if_exception_type(BadRequestError),
        reraise=True,
    )
    def attempt_submit_job(self, file: FileObject) -> FineTuningJob:
        return self.openai.fine_tuning.jobs.create(
            model=self.config.base_model,
            training_file=file.id,
        )

    def create_job(self, live: PreviewLive) -> FineTuningJob:
        if self.config.job_id:
            return self.poll_job_status()

        with live.progress.open(self.config.examples_file, "rb", description=f"Uploading {self.config.examples_file}...") as fp:
            file = self.openai.files.create(
                file=fp,
                purpose="fine-tune",
            )

        job = self.attempt_submit_job(file)

        self.config.job_id = job.id
        return job

    def fine_tune(self) -> None:
        with PreviewLive() as live:
            job = self.create_job(live)

            self.dedent_print(f"""
                [bold]Fine-tuning is starting...[/]
                View it online at: https://platform.openai.com/finetune/{job.id}
                    Created at: {datetime.fromtimestamp(job.created_at)}
                    Base Model: {job.model}

                [italic dim]Closing this terminal will not stop the fine-tuning. This will take a while...
            """)  # noqa: DTZ006

            task_id = live.progress.add_task("", total=None)

            while job.status not in {"succeeded", "failed", "cancelled"}:
                job = self.poll_job_status()

                live.progress.update(
                    task_id,
                    total=job.estimated_finish,
                    description=f"Fine-tuning: [italic]{job.status.replace('_', ' ').title()}[/]...",
                )

                sleep(1)

        self.process_completed_job(job)

    def get_cost_string(self, total_tokens: int) -> str:
        return f"${self.config.token_price / 1000000 * total_tokens:.2f}"

    def print_estimates(self) -> None:
        total_tokens = self.config.expected_epochs * self.estimated_tokens
        cost_string = self.get_cost_string(total_tokens)

        self.dedent_print(f"""
            Tokens {self.estimated_tokens:,}:
            Total tokens for [bold orange1]{self.config.expected_epochs}[/] epoch(s): {total_tokens:,}
            Expected cost when trained with [bold purple]{self.config.base_model}[/]: {cost_string}
            NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                    [italic red]Amelia, Mutsumi, and Marin are not responsible for any inaccuracies in the token count or estimated price.[/]
        """)
