from json import dump
from pathlib import Path

from more_itertools import last

from tumblrbot.models import Post, PostsResponse
from tumblrbot.utils import PreviewLive, UtilClass


class PostDownloader(UtilClass):
    def paginate_posts(self, blog_name: str, before: int, completed: int, download_path: Path, live: PreviewLive) -> None:
        with download_path.open("a", encoding="utf_8") as fp:
            task_id = live.progress.add_task(f"Downloading posts from '{blog_name}'...", total=None, completed=completed)

            while True:
                response = self.tumblr.retrieve_published_posts(blog_name, before)
                response_object = PostsResponse.model_validate_json(response.text)

                live.progress.update(task_id, total=response_object.response.blog.posts)

                for post in response_object.response.posts:
                    dump(post, fp)
                    fp.write("\n")

                    post_object = Post.model_validate(post)
                    before = post_object.timestamp

                    live.progress.update(task_id, advance=1)
                    live.custom_update(post_object)

                if not response_object.response.posts:
                    break

    def get_download_path(self, blog_name: str) -> Path:
        return (self.config.training.data_directory / blog_name).with_suffix(".jsonl")

    def get_download_paths(self) -> list[Path]:
        return list(map(self.get_download_path, self.config.training.blog_names))

    def download(self) -> None:
        self.config.training.data_directory.mkdir(parents=True, exist_ok=True)

        with PreviewLive() as live:
            for blog_name in self.config.training.blog_names:
                download_path = self.get_download_path(blog_name)
                lines = download_path.read_text("utf_8").splitlines() if download_path.exists() else []

                self.paginate_posts(
                    blog_name,
                    Post.model_validate_json(last(lines, "{}")).timestamp,
                    len(lines),
                    download_path,
                    live,
                )
