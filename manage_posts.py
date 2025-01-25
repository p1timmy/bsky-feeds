#! /usr/bin/env python3
import logging
import re
import readline  # noqa: F401

import click
from peewee import Model, ModelSelect

logging.basicConfig(level=logging.CRITICAL)

from server.database import Post  # noqa: E402

BSKY_POST_URL_REGEX = re.compile(
    r"https://bsky.app/profile/(?:[A-Za-z0-9\-\.]+\.[a-z]+|did:plc:[a-z2-7]{24})/post/([a-z2-7]{13})"
)
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _echo_and_abort(message: str):
    click.secho(message, fg="red", bold=True)
    raise click.Abort()


@click.group(
    context_settings=CONTEXT_SETTINGS, help="Manage Bluesky posts in feed database"
)
def cli():
    pass


@cli.command()
@click.argument("post_uri", nargs=-1, required=True, type=click.STRING)
def remove(post_uri: tuple[str, ...]):
    """
    Remove posts from all feeds

    POST_URI is 1 or more bsky.app URLs of the post(s) to remove
    """
    post_uris = set(post_uri)
    tids: set[str] = set()
    for uri in post_uris:
        try:
            tids.add(BSKY_POST_URL_REGEX.findall(uri).pop())
        except IndexError:
            _echo_and_abort(f"Not a valid URI: {uri}")

    query: ModelSelect = Post.select()
    for tid in tids:
        query = query.orwhere(Post.uri.endswith(f"/{tid}"))

    db_ids = set(post.id for post in query)
    if not db_ids:
        _echo_and_abort("No matching posts found in database")

    feed_post_through: Model = Post.feeds.get_through_model()
    num_posts_in_feeds: int = (
        feed_post_through.select().where(feed_post_through.post_id.in_(db_ids)).count()
    )

    uri_count = len(post_uris)
    click.echo(
        f"{len(db_ids)}/{uri_count} post{'' if uri_count == 1 else 's'} found in"
        f" database, {num_posts_in_feeds} of them are in feeds."
    )

    if num_posts_in_feeds < 1:
        click.secho("Nothing to do here", fg="green", bold=True)
        return

    if click.confirm(
        f"Remove {num_posts_in_feeds} post{'' if num_posts_in_feeds == 1 else 's'} from"
        " all feeds in database?",
        abort=True,
    ):
        # FIXME: Ask to retry query if DB is locked
        feed_post_through.delete().where(
            feed_post_through.post_id.in_(db_ids)
        ).execute()
        click.secho("All done! Posts removed successfully", fg="green", bold=True)


if __name__ == "__main__":
    cli()
