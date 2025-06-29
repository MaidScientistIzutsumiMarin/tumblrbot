from datetime import datetime
from time import sleep, time

from openai import OpenAI
from openai.types.fine_tuning import FineTuningJob

from tumblrbot.settings import CONFIG
from tumblrbot.utils import PreviewLive, dedent_print


def get_total_tokens(tokens: int) -> int:
    return CONFIG.training.expected_epochs * tokens


def get_cost_string(total_tokens: int) -> str:
    return f"${CONFIG.training.token_price / 1000000 * total_tokens:.2f}"


def get_time_delta(job: FineTuningJob, offset: float) -> float:
    return offset - job.created_at


def print_estimates(tokens: int) -> None:
    total_tokens = get_total_tokens(tokens)

    dedent_print(f"""
        Tokens {tokens:,}:
        Total tokens for [bold orange1]{CONFIG.training.expected_epochs}[/] epoch(s): {total_tokens:,}
        Expected cost when trained with [bold purple]{CONFIG.base_model}[/]: {get_cost_string(total_tokens)}
        NOTE: Token values are approximate and may not be 100% accurate, please be aware of this when using the data.
                [italic red]Neither Amelia nor Mutsumi are responsible for any inaccuracies in the token count or estimated price.[/]
    """)


def poll_job_status(job_id: str, openai: OpenAI, tokens: int) -> FineTuningJob:
    job = openai.fine_tuning.jobs.retrieve(job_id)

    if CONFIG.training.expected_epochs != job.hyperparameters.n_epochs and isinstance(job.hyperparameters.n_epochs, int):
        CONFIG.training.expected_epochs = job.hyperparameters.n_epochs
        CONFIG.model_post_init()

        dedent_print(f"""
            The number of epochs has been updated to {job.hyperparameters.n_epochs}!
            [cyan]Updated the config.
        """)
        print_estimates(tokens)

    return job


def main(openai: OpenAI, tokens: int) -> None:
    if CONFIG.training.job_id:
        job = openai.fine_tuning.jobs.retrieve(CONFIG.training.job_id)
    else:
        file = openai.files.create(
            file=CONFIG.training.output_file,
            purpose="fine-tune",
        )
        job = openai.fine_tuning.jobs.create(
            model=CONFIG.base_model,
            training_file=file.id,
        )

        CONFIG.training.job_id = job.id
        CONFIG.model_post_init()

    with PreviewLive() as live:
        dedent_print(f"""
            [bold]Fine-tuning is starting...[/]
            View it online at: https://platform.openai.com/finetune/{job.id}
                Created at: {datetime.fromtimestamp(job.created_at)}
                Base Model: {job.model}

            [italic dim]Closing this terminal will not stop the fine-tuning. This will take a while...
        """)  # noqa: DTZ006

        task_id = live.progress.add_task("", total=None)

        while job.status not in {"succeeded", "failed", "cancelled"}:
            poll_job_status(job.id, openai, tokens)

            live.progress.update(
                task_id,
                total=job.estimated_finish - job.created_at if job.estimated_finish else None,
                completed=time() - job.created_at,
                description=f"Fine-tuning is {job.status.replace('_', ' ')}...",
            )

            sleep(1)

    if job.trained_tokens is not None:
        dedent_print(f"""
            Trained Tokens: {job.trained_tokens:,}
            Cost: {get_cost_string(job.trained_tokens)}
        """)

    if job.status == "failed" and job.error is not None:
        msg = f"Error: {job.error.message}"
        raise RuntimeError(msg)

    CONFIG.generation.fine_tuned_model = job.fine_tuned_model or ""
    CONFIG.training.job_id = ""
    CONFIG.model_post_init()
