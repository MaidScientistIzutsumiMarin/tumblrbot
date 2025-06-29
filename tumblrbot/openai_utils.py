from datetime import datetime
from math import ceil
from time import sleep, time
from typing import Literal

import rich
from hishel import CacheTransport, FileStorage
from httpx import HTTPTransport
from more_itertools import chunked
from openai import DefaultHttpxClient, OpenAI
from openai.types.fine_tuning import FineTuningJob
from openai.types.responses import ParsedResponse
from pydantic import BaseModel
from rich.console import Console
from tiktoken import Encoding, encoding_for_model, get_encoding

from tumblrbot.settings import CONFIG, TOKENS
from tumblrbot.tumblr_utils import TumblrSession
from tumblrbot.utils import Post, PreviewLive, dedent_print, yes_no_prompt


class Example(BaseModel):
    class Message(BaseModel):
        content: str
        role: Literal["developer", "user", "assistant"]

    messages: list[Message]


class OpenAISession(OpenAI):
    def __init__(self) -> None:
        super().__init__(
            api_key=TOKENS.openai_api_key,
            http_client=DefaultHttpxClient(
                http2=True,
                transport=CacheTransport(
                    HTTPTransport(),
                    FileStorage(),
                ),
            ),
        )

    def write_examples(self, *, should_write: bool) -> int:
        try:
            encoding = encoding_for_model(CONFIG.base_model)
        except KeyError as error:
            encoding = get_encoding("o200k_base")
            Console(stderr=True, style="logging.level.warning").print(f"[Warning] Using encoding '{encoding.name}': {''.join(error.args)}\n")

        CONFIG.training.output_file.parent.mkdir(parents=True, exist_ok=True)

        posts = [post for post in Post.get() if post.get_text_content() and not (post.is_submission or post.trail)]
        if should_write and yes_no_prompt("Remove posts flagged by the OpenAI moderation? This can sometimes resolve errors with fine-tuning validation, but is slow."):
            filtered_posts: list[Post] = []
            with PreviewLive() as live:
                for chunk in live.progress.track(
                    chunked(posts, 32),
                    ceil(len(posts) / 32),
                    description="Removing flagged posts...",
                ):
                    response = self.moderations.create(input=list(map(Post.get_text_content, chunk)))
                    for post, moderation in zip(chunk, response.results, strict=True):
                        if moderation.flagged:
                            live.custom_update(post)
                        else:
                            filtered_posts.append(post)
        else:
            filtered_posts = posts

        tokens = 0
        mode = "w" if should_write else "a"
        with CONFIG.training.output_file.open(mode, encoding="utf_8") as fp:
            for post in filtered_posts:
                example = Example(
                    messages=[
                        Example.Message(role="developer", content=CONFIG.developer_message),
                        Example.Message(role="user", content=CONFIG.user_input),
                        Example.Message(role="assistant", content=post.get_text_content()),
                    ],
                )
                if should_write:
                    fp.write(f"{example.model_dump_json()}\n")

                tokens += count_tokens(example, encoding)

        print_estimates(tokens)
        rich.print(f"[bold]The training data can be found at: '{CONFIG.training.output_file}'\n")

        return tokens

    def poll_job_status(self, job_id: str, tokens: int) -> FineTuningJob:
        job = self.fine_tuning.jobs.retrieve(job_id)

        if CONFIG.training.expected_epochs != job.hyperparameters.n_epochs and isinstance(job.hyperparameters.n_epochs, int):
            CONFIG.training.expected_epochs = job.hyperparameters.n_epochs
            CONFIG.model_post_init()

            dedent_print(f"""
                The number of epochs has been updated to {job.hyperparameters.n_epochs}!
                [cyan]Updated the config.
            """)
            print_estimates(tokens)

        return job

    def start_fine_tuning(self, tokens: int) -> None:
        if CONFIG.training.job_id:
            job = self.fine_tuning.jobs.retrieve(CONFIG.training.job_id)
        else:
            file = self.files.create(
                file=CONFIG.training.output_file,
                purpose="fine-tune",
            )
            job = self.fine_tuning.jobs.create(
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
                job = self.poll_job_status(job.id, tokens)

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

        CONFIG.training.job_id = ""
        CONFIG.model_post_init()

        if job.status == "failed" and job.error is not None:
            raise RuntimeError(job.error.message)

        if job.fine_tuned_model:
            CONFIG.generation.fine_tuned_model = job.fine_tuned_model or ""
            CONFIG.model_post_init()

    def generate_content(self) -> ParsedResponse[Post]:
        return self.responses.parse(
            input=CONFIG.user_input,
            model=CONFIG.generation.fine_tuned_model,
            text_format=Post,
            instructions=CONFIG.developer_message,
        )

    def generate_tags(self, response_id: str) -> Post | None:
        return self.responses.parse(
            input="Extract the most important subjects.",
            model=CONFIG.base_model,
            text_format=Post,
            instructions="You are an advanced text summarization tool. You return the requested data to the user.",
            previous_response_id=response_id,
        ).output_parsed

    def generate_post(self) -> Post | None:
        response = self.generate_content()
        if response.output_parsed and (tags := self.generate_tags(response.id)):
            response.output_parsed.tags = tags.tags
        return response.output_parsed

    def create_drafts(self, tumblr: TumblrSession) -> None:
        message = f"View drafts here: https://tumblr.com/blog/{CONFIG.generation.blog_name}/drafts"

        with PreviewLive() as live:
            for i in live.progress.track(range(CONFIG.generation.draft_count), description="Generating drafts..."):
                try:
                    if post := self.generate_post():
                        tumblr.create_draft_post(post)
                        live.custom_update(post)
                except BaseException as exc:
                    exc.add_note(f"📉 An error occurred! Generated {i} draft(s) before failing. {message}")
                    raise

        rich.print(f":chart_increasing: [bold green]Generated {CONFIG.generation.draft_count} draft(s).[/] {message}")


def count_tokens(example: Example, encoding: Encoding) -> int:
    # Based on https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
    # and https://cookbook.openai.com/examples/chat_finetuning_data_prep
    num_tokens = 3 * (len(example.messages) + 1)  # every reply is primed with <|start|>assistant<|message|>
    for message in example.messages:
        num_tokens += len(encoding.encode(message.content))
    return num_tokens


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
