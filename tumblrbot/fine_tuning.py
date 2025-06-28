from datetime import datetime
from time import sleep, time

from openai import OpenAI

from tumblrbot.settings import CONFIG
from tumblrbot.utils import PreviewLive, dedent_print, get_cost_string


def main(openai: OpenAI, tokens: int) -> None:
    file = openai.files.create(
        file=CONFIG.training.output_file,
        purpose="fine-tune",
    )
    job = openai.fine_tuning.jobs.create(
        model=CONFIG.model_name,
        training_file=file.id,
    )

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
            job = openai.fine_tuning.jobs.retrieve(job.id)

            if CONFIG.training.estimated_epochs != job.hyperparameters.n_epochs and isinstance(job.hyperparameters.n_epochs, int):
                dedent_print(f"""
                    The number of epochs has been updated to {job.hyperparameters.n_epochs}!
                    [bold]The estimated price is now {get_cost_string(job.hyperparameters.n_epochs * tokens)}![/]
                    [cyan]Updating the value in the config...
                """)
                CONFIG.training.estimated_epochs = job.hyperparameters.n_epochs
                CONFIG.model_post_init()

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
    CONFIG.model_post_init()
