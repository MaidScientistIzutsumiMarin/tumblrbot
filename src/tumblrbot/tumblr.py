from collections.abc import Iterable
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError, run

import rich
from requests_oauthlib import OAuth1Session
from rich.prompt import Prompt
from tumblr_backup.main import EXIT_NOPOSTS

from src.tumblrbot.common import yes_no_prompt


def generate_oauth_tokens() -> tuple[str, str, str, str]:
    rich.print("Retrieve a consumer key and consumer secret from: http://tumblr.com/oauth/apps")
    consumer_key = Prompt.ask("Enter the consumer key").strip()
    consumer_secret = Prompt.ask("Enter the consumer secret").strip()

    # STEP 1: Obtain request token
    session = OAuth1Session(consumer_key, consumer_secret)
    response = session.fetch_request_token("http://tumblr.com/oauth/request_token")

    # STEP 2: Authorize URL + Response
    authorization_url = session.authorization_url("http://tumblr.com/oauth/authorize")

    # Redirect to authentication page
    rich.print(f"\nGo here and press 'Allow': {authorization_url}")
    url = Prompt.ask("Enter the full redirected URL").strip()

    # STEP 3: Request final access token
    session = OAuth1Session(
        consumer_key,
        consumer_secret,
        response["oauth_token"],
        response["oauth_token_secret"],
        verifier=session.parse_authorization_response(url)["oauth_verifier"],
    )
    tokens = session.fetch_access_token("http://tumblr.com/oauth/access_token")

    rich.print("Successfully generated tokens!\n")
    return consumer_key, consumer_secret, tokens["oauth_token"], tokens["oauth_token_secret"]


def download_posts(tumblr_consumer_key: str, blognames: Iterable[str], data_directory: Path) -> list[Path]:
    should_download = yes_no_prompt("Download latest posts?", default=True)

    tumblr_backup_filename = "tumblr-backup"
    tumblr_backup_path = which(tumblr_backup_filename) or ""

    try:
        run(
            [tumblr_backup_path, "--set-api-key", tumblr_consumer_key],
            check=True,
        )
    except FileNotFoundError as error:
        error.filename = tumblr_backup_filename
        raise

    post_paths: list[Path] = []
    for blogname in blognames:
        output_directory = data_directory / blogname

        if should_download:
            try:
                run(
                    [tumblr_backup_path, blogname, "--outdir", output_directory, "--incremental", "--skip-images", "--json", "--type", "text", "--no-reblog"],
                    check=True,
                )
            except CalledProcessError as error:
                if error.returncode != EXIT_NOPOSTS:
                    raise

        post_paths += (output_directory / "json").iterdir()
    return post_paths
