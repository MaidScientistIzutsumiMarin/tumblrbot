from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from time import sleep, time

import rich
from openai.types.fine_tuning import FineTuningJob

from tumblrbot.utils import PreviewLive, UtilClass, yes_no_prompt


@dataclass
class FineTuner(UtilClass):
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

        self.config.training.job_id = ""
        self.config.model_post_init()

        if job.status == "failed" and job.error is not None:
            if yes_no_prompt("Should the failed file be removed from OpenAI?"):
                self.openai.files.delete(job.training_file)
                rich.print("[green]File deleted!\n")

            raise RuntimeError(job.error.message)

        if job.fine_tuned_model:
            self.config.generation.fine_tuned_model = job.fine_tuned_model or ""
            self.config.model_post_init()

    def poll_job_status(self) -> FineTuningJob:
        job = self.openai.fine_tuning.jobs.retrieve(self.config.training.job_id)

        if self.config.training.expected_epochs != job.hyperparameters.n_epochs and isinstance(job.hyperparameters.n_epochs, int):
            self.config.training.expected_epochs = job.hyperparameters.n_epochs
            self.config.model_post_init()

            self.dedent_print(f"""
                The number of epochs has been updated to {job.hyperparameters.n_epochs}!
                [cyan]Updated the config.
            """)
            self.print_estimates()

        return job

    def create_job(self) -> FineTuningJob:
        if self.config.training.job_id:
            return self.poll_job_status()

        file = self.openai.files.create(
            file=self.config.training.output_file,
            purpose="fine-tune",
        )
        job = self.openai.fine_tuning.jobs.create(
            model=self.config.base_model,
            training_file=file.id,
        )

        self.config.training.job_id = job.id
        self.config.model_post_init()
        return job

    def fine_tune(self) -> None:
        job = self.create_job()

        self.dedent_print(f"""
            [bold]Fine-tuning is starting...[/]
            View it online at: https://platform.openai.com/finetune/{job.id}
                Created at: {datetime.fromtimestamp(job.created_at)}
                Base Model: {job.model}

            [italic dim]Closing this terminal will not stop the fine-tuning. This will take a while...
        """)  # noqa: DTZ006

        with PreviewLive() as live:
            task_id = live.progress.add_task("", total=None)

            while job.status not in {"succeeded", "failed", "cancelled"}:
                job = self.poll_job_status()

                live.progress.update(
                    task_id,
                    total=job.estimated_finish - job.created_at if job.estimated_finish else None,
                    completed=time() - job.created_at,
                    description=f"Fine-tuning is {job.status.replace('_', ' ')}...",
                )

                sleep(1)

        self.process_completed_job(job)

    def get_cost_string(self, total_tokens: int) -> str:
        return f"${self.config.training.token_price / 1000000 * total_tokens:.2f}"

    def print_estimates(self) -> None:
        total_tokens = self.config.training.expected_epochs * self.estimated_tokens
        cost_string = self.get_cost_string(total_tokens)

        self.dedent_print(f"""
            Tokens {self.estimated_tokens:,}:
            Total tokens for [bold orange1]{self.config.training.expected_epochs}[/] epoch(s): {total_tokens:,}
            Expected cost when trained with [bold purple]{self.config.base_model}[/]: {cost_string}
            NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                    [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]
        """)
