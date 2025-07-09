from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from time import sleep, time

import rich
from openai.types.fine_tuning import FineTuningJob
from rich import progress
from rich.prompt import Confirm

from tumblrbot.utils.common import FlowClass, PreviewLive


@dataclass
class FineTuner(FlowClass):
    estimated_tokens: int

    @staticmethod
    def dedent_print(text: str) -> None:
        rich.print(dedent(text).lstrip())

    def fine_tune(self) -> None:
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
                    total=job.estimated_finish - job.created_at if job.estimated_finish else None,
                    completed=time() - job.created_at,
                    description=f"Fine-tuning: [italic]{job.status.replace('_', ' ').title()}[/]...",
                )

                sleep(1)

        self.process_completed_job(job)

    def create_job(self) -> FineTuningJob:
        if self.config.job_id:
            return self.poll_job_status()

        with progress.open(self.config.examples_file, "rb", description=f"Uploading [purple]{self.config.examples_file}[/]...") as fp:
            file = self.openai.files.create(
                file=fp,
                purpose="fine-tune",
            )
        rich.print()

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
                Trained Tokens: {job.trained_tokens:,}
                Cost: {self.get_cost_string(job.trained_tokens)}
            """)

        self.config.job_id = ""

        if job.status != "succeeded":
            if Confirm.ask("[gray62]Delete uploaded examples file?", default=False):
                self.openai.files.delete(job.training_file)
                rich.print()

            if job.status == "failed" and job.error is not None:
                raise RuntimeError(job.error.message)

        if job.fine_tuned_model:
            self.config.fine_tuned_model = job.fine_tuned_model or ""

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

    def get_cost_string(self, total_tokens: int) -> str:
        return f"${self.config.token_price / 1000000 * total_tokens:.2f}"
