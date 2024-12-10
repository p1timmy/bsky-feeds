#! /usr/bin/env python3
import re
import readline  # noqa: F401

import click
from peewee import Model, ModelSelect, SqliteDatabase

from server.database import Post

BSKY_POST_URL_REGEX = re.compile(
    r"https://bsky.app/profile/(?:[A-Za-z0-9\-\.]+\.[a-z]+|did:plc:[a-z2-7]{24})/post/([a-z2-7]{13})"
)


def _close_db(db: SqliteDatabase):
    if not db.is_closed():
        db.close()


def _fail_exit(message: str, db: SqliteDatabase):
    click.echo(click.style(message, fg="red", bold="true"))
    _close_db(db)
    exit(1)


def main(db: SqliteDatabase):
    urls: list[str] = []
    post_ids: list[str] = []

    while True:
        prompt_message = "Enter a Bluesky post URL"
        if urls:
            prompt_message = f"{prompt_message} or press Enter to continue"

        url: str = click.prompt(
            prompt_message, default="", type=str, show_default=False
        ).strip()
        if not url:
            break

        try:
            post_id: str = BSKY_POST_URL_REGEX.findall(url).pop()
        except IndexError:
            click.echo(click.style("Invalid URL", fg="red"))
        else:
            if post_id not in post_ids:
                post_ids.append(post_id)
                urls.append(url)
                click.echo(click.style("Post URL added", fg="green"))
            else:
                click.echo(click.style("Post URL already added", fg="yellow"))

    if not urls:
        _fail_exit("No post URLs provided, exiting...", db)

    if db.is_closed():
        db.connect()

    query: ModelSelect = Post.select()
    for post_id in post_ids:
        query = query.orwhere(Post.uri.endswith(f"/{post_id}"))

    db_ids = [post.id for post in query]
    if not db_ids:
        _fail_exit("No matching posts found in database, exiting...", db)

    feed_post_through: Model = Post.feeds.get_through_model()
    num_posts_in_feeds: int = (
        feed_post_through.select().where(feed_post_through.post_id.in_(db_ids)).count()
    )

    url_count = len(urls)
    click.echo(
        f"{len(db_ids)}/{url_count} post{'' if url_count == 1 else 's'} found in"
        f" database, {num_posts_in_feeds} of them are in feeds."
    )

    if num_posts_in_feeds < 1:
        click.echo(click.style("Nothing to do here, exiting...", fg="green", bold=True))
    elif click.confirm(
        f"Remove {num_posts_in_feeds} post{'' if num_posts_in_feeds == 1 else 's'} from"
        " all feeds in database? This action is not undoable!",
        abort=True,
    ):
        # FIXME: Ask to retry query if DB is locked
        feed_post_through.delete().where(
            feed_post_through.post_id.in_(db_ids)
        ).execute()
        click.echo(click.style("All done!", fg="green", bold=True))

    _close_db(db)


if __name__ == "__main__":
    db = SqliteDatabase("feed_database.db")
    try:
        main(db)
    except click.Abort:
        _fail_exit("Script aborted, exiting...", db)
