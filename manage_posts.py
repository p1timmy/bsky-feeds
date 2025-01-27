#! /usr/bin/env python3
import logging
import re
import readline  # noqa: F401
import typing as t
from datetime import datetime

import click
from peewee import Model, ModelSelect

logging.basicConfig(level=logging.CRITICAL)

from server.database import Feed, Post, db  # noqa: E402

BSKY_POST_URL_REGEX = re.compile(
    r"https://bsky.app/profile/([A-Za-z0-9\-\.]+\.[a-z]+|did:plc:[a-z2-7]{24})/post/([a-z2-7]{13})"
)
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


if t.TYPE_CHECKING:
    from atproto_client.models.app.bsky.feed.defs import PostView
    from atproto_client.models.app.bsky.feed.post import Record


def _get_api_client():
    # BUG: We have to do the import here due to Pydantic being slow to load
    # (https://github.com/MarshalX/atproto/issues/453,
    # https://github.com/pydantic/pydantic/issues/9908)
    from server.api_client import get_client

    return get_client()


def _echo_and_abort(message: str):
    click.secho(message, fg="red", bold=True)
    raise click.Abort()


def _get_post_tid_or_abort(uri: str) -> str:
    try:
        return BSKY_POST_URL_REGEX.findall(uri)[0][-1]
    except IndexError:
        _echo_and_abort(f"Not a valid URI: {uri}")


@click.group(
    context_settings=CONTEXT_SETTINGS, help="Manage Bluesky posts in feed database"
)
def cli():
    pass


@cli.command()
@click.argument("feed", nargs=1, required=True, type=click.STRING)
@click.argument("post_uri", nargs=-1, required=True, type=click.STRING)
def add(feed: str, post_uri: tuple[str, ...]):
    """
    Add posts to a feed

    FEED is a feed name as listed in the server/algos directory
    POST_URI is 1 or more bsky.app URLs of the post(s) to add
    """

    feed_row = Feed.get_or_none(Feed.algo_name == feed)
    if feed_row is None:
        _echo_and_abort(f"Feed name not found in database: {feed}")

    posts_to_add: list[Post] = []
    uris_to_get: list[str] = []

    # Check if post exists in DB
    for uri in post_uri:
        tid = _get_post_tid_or_abort(uri)
        post: Post | None = Post.get_or_none(Post.uri.endswith(f"/{tid}"))
        if post is None:
            uris_to_get.append(uri)
        else:
            posts_to_add.append(post)

    # Get missing posts from API and add them to DB
    if uris_to_get:
        click.confirm(
            "Need to fetch metadata for"
            f" {len(uris_to_get)} post{'s' if len(uris_to_get) != 1 else ''},"
            " continue?",
            abort=True,
        )

        at_uris_to_get: list[str] = []
        client = _get_api_client()
        for uri in uris_to_get:
            author, tid = BSKY_POST_URL_REGEX.findall(uri)[0]
            response = client.get_post(tid, author)
            if response is None:
                click.echo(f"Failed to get post URL: {uri}", fg="red")
            else:
                at_uris_to_get.append(response.uri)

        response = client.get_posts(at_uris_to_get)

        posts_to_create: list[dict] = []
        post: PostView
        for post in response.posts:
            record: Record = post.record
            reply_root = reply_parent = None
            if record.reply:
                reply_root = record.reply.root.uri
                reply_parent = record.reply.parent.uri

            posts_to_create.append(
                {
                    "uri": post.uri,
                    "cid": post.cid,
                    "author_did": post.author.did,
                    "reply_parent": reply_parent,
                    "reply_root": reply_root,
                    "indexed_at": datetime.fromisoformat(post.indexed_at),
                }
            )

        if posts_to_create:
            with db.atomic():
                for post_dict in posts_to_create:
                    posts_to_add.append(Post.create(**post_dict))

            click.echo(
                f"Added {len(posts_to_create)}/{len(at_uris_to_get)} posts to database"
            )

    # Add the posts to feed
    added_count = 0
    with db.atomic():
        for post in posts_to_add:
            if feed_row not in post.feeds:
                post.feeds.add([feed_row])
                added_count += 1

    if added_count > 0:
        click.secho(
            f'All done! Posts added to "{feed}" feed: {added_count}',
            fg="green",
            bold=True,
        )
    else:
        click.secho(
            f'All posts already included in "{feed}" feed, nothing to do',
            fg="green",
            bold=True,
        )


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
        tids.add(_get_post_tid_or_abort(uri))

    query: ModelSelect = Post.select()
    for tid in tids:
        query = query.orwhere(Post.uri.endswith(f"/{tid}"))

    db_ids = set(post.id for post in query)
    if not db_ids:
        _echo_and_abort("No matching posts found in database")

    feed_post_through: Model = Post.feeds.get_through_model()
    num_posts_in_feeds: int = (
        feed_post_through.select(feed_post_through.post_id)
        .distinct()
        .where(feed_post_through.post_id.in_(db_ids))
        .count()
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
