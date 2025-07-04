from io import TextIOBase
from json import dump
from pathlib import Path

from tumblrbot.utils.common import PreviewLive, UtilClass
from tumblrbot.utils.models import Post


class PostDownloader(UtilClass):
    def paginate_posts(self, blog_identifier: str, offset: int, fp: TextIOBase, live: PreviewLive) -> None:
        task_id = live.progress.add_task(f"Downloading posts from '{blog_identifier}'...", total=None, completed=offset)

        while True:
            response = self.tumblr.retrieve_published_posts(blog_identifier, offset).json()["response"]
            live.progress.update(task_id, total=response["blog"]["posts"], completed=offset)

            if posts := response["posts"]:
                for post in posts:
                    dump(post, fp)
                    fp.write("\n")

                    model = Post.model_validate(post)
                    live.custom_update(model)

                offset += len(posts)
            else:
                break

    def get_data_path(self, blog_identifier: str) -> Path:
        return (self.config.data_directory / blog_identifier).with_suffix(".jsonl")

    def get_data_paths(self) -> list[Path]:
        return list(map(self.get_data_path, self.config.download_blog_identifiers))

    def download(self) -> None:
        self.config.data_directory.mkdir(parents=True, exist_ok=True)

        with PreviewLive() as live:
            for blog_identifier in self.config.download_blog_identifiers:
                data_path = self.get_data_path(blog_identifier)

                with data_path.open("a", encoding="utf_8") as fp:
                    self.paginate_posts(
                        blog_identifier,
                        len(data_path.read_text("utf_8").splitlines()) if data_path.exists() else 0,
                        fp,
                        live,
                    )
