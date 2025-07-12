from io import TextIOBase
from json import dump
from typing import override

from tumblrbot.utils.common import FlowClass, PreviewLive
from tumblrbot.utils.models import Post


class PostDownloader(FlowClass):
    @override
    def main(self) -> None:
        self.config.data_directory.mkdir(parents=True, exist_ok=True)

        with PreviewLive() as live:
            for blog_identifier in self.config.download_blog_identifiers:
                data_path = self.get_data_path(blog_identifier)

                completed = 0
                after = 0
                if data_path.exists():
                    lines = data_path.read_text("utf_8").splitlines() if data_path.exists() else []
                    completed = len(lines)
                    if lines:
                        after = Post.model_validate_json(lines[-1]).timestamp

                with data_path.open("a", encoding="utf_8") as fp:
                    self.paginate_posts(
                        blog_identifier,
                        completed,
                        after,
                        fp,
                        live,
                    )

    def paginate_posts(self, blog_identifier: str, completed: int, after: int, fp: TextIOBase, live: PreviewLive) -> None:
        task_id = live.progress.add_task(f"Downloading posts from '{blog_identifier}'...", total=None, completed=completed)

        while True:
            response = self.tumblr.retrieve_published_posts(blog_identifier, after=after).json()["response"]
            live.progress.update(task_id, total=response["blog"]["posts"], completed=completed)

            if posts := response["posts"]:
                for post in posts:
                    dump(post, fp)
                    fp.write("\n")

                    model = Post.model_validate(post)
                    after = model.timestamp
                    live.custom_update(model)

                completed += len(posts)
            else:
                return
