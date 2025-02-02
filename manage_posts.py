#! /usr/bin/env python3
import logging
import re
import readline  # noqa: F401
import typing as t
from datetime import datetime
from itertools import batched

import click
from peewee import Model, ModelSelect

logging.basicConfig(level=logging.CRITICAL)

from server.database import Feed, Post, db  # noqa: E402

BSKY_POST_URL_REGEX = re.compile(
    r"https://bsky.app/profile/([A-Za-z0-9\-\.]+\.[a-z]+|did:plc:[a-z2-7]{24})/post/([a-z2-7]{13})"
)
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 999,
}


if t.TYPE_CHECKING:
    from atproto_client.models.app.bsky.feed.defs import PostView
    from atproto_client.models.app.bsky.feed.post import GetRecordResponse, Record


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


def _get_feed_row_by_name_or_abort(feed_name: str) -> Feed:
    row = Feed.get_or_none(Feed.algo_name == feed_name)
    if row is None:
        _echo_and_abort(f"Feed name not found in database: {feed_name}")

    return row


@click.group(
    context_settings=CONTEXT_SETTINGS, help="Manage Bluesky posts in feed database"
)
def cli():
    pass


@cli.command()
@click.argument("feed", nargs=1, required=True, type=click.STRING)
@click.argument("post_uri", nargs=-1, required=True, type=click.STRING)
@click.option("-y", "--noconfirm", is_flag=True, help="Skip confirmation prompts")
def add(feed: str, post_uri: tuple[str, ...], noconfirm: bool):
    """
    Add posts to a feed

    FEED is a feed name as listed in the server/algos directory (any of those that don't
    start with an underscore)

    POST_URI is 1 or more bsky.app URLs of the post(s) to add
    \f

    :param feed: Name of the feed to add posts into. Must be one of the module
        names listed in `server/algos` directory.
    :param post_uri: `tuple` of bsky.app URLs of posts to add to feed
    :param noconfirm: Whether to skip confirmation prompts or not
    """

    # Check if feed name exists in DB
    feed_row = _get_feed_row_by_name_or_abort(feed)

    posts_to_add: list[Post] = []
    uris_to_get: list[str] = []

    # Check if post exists in DB
    for uri in set(post_uri):
        tid = _get_post_tid_or_abort(uri)
        post: Post | None = Post.get_or_none(Post.uri.endswith(f"/{tid}"))
        if post is None:
            uris_to_get.append(uri)
        else:
            posts_to_add.append(post)

    # Get missing posts from API and add them to DB
    if uris_to_get:
        uris_to_get_count_str = (
            f"{len(uris_to_get)} post{'s' if len(uris_to_get) != 1 else ''}"
        )
        if not noconfirm:
            click.confirm(
                f"Need to fetch metadata for {uris_to_get_count_str}, continue?",
                abort=True,
            )

        click.echo(f"Getting metadata for {uris_to_get_count_str}...")

        # Do ATProto SDK imports here due to (again) Pydantic being slow to load
        from atproto_client.exceptions import RequestErrorBase
        from atproto_client.models.common import XrpcError
        from atproto_client.request import Response as RequestResponse

        at_uris_to_get: list[str] = []
        client = _get_api_client()
        for uri in uris_to_get:
            author, tid = BSKY_POST_URL_REGEX.findall(uri)[0]
            try:
                response: GetRecordResponse = client.get_post(tid, author)
            except RequestErrorBase as e:
                response: RequestResponse = e.response

            if response is None or (
                isinstance(response, RequestResponse) and response.success is False
            ):
                # Skip if post in URL can't be found for some reason
                click.secho(f"Failed to get post URL: {uri}", fg="red")
                if response is not None:
                    reason = f"({response.status_code})"
                    error = response.content
                    if isinstance(error, XrpcError):
                        reason = f"{reason} {error.error}"
                        if error.message:
                            reason = f"{reason} - {error.message}"
                    else:
                        reason = f"{reason} {error}"

                    click.secho(reason, fg="red", dim=True)
            else:
                at_uris_to_get.append(response.uri)

        if at_uris_to_get:
            posts_to_create: list[dict] = []
            for chunk in batched(at_uris_to_get, 25):
                response = client.get_posts(list(chunk))

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
                f"Added {len(posts_to_create)}/{len(uris_to_get)}"
                f" post{'s' if len(uris_to_get) != 1 else ''} to database"
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
    elif posts_to_add:
        click.secho(
            f'All {"other " if uris_to_get else ""}posts already included in "{feed}"'
            " feed, nothing to do",
            fg="green",
            bold=True,
        )
    else:
        click.secho(f'No posts were added to "{feed}" feed', fg="red", bold=True)
        raise click.exceptions.Exit(1)


@cli.command()
@click.argument("post_uri", nargs=-1, required=True, type=click.STRING)
@click.option(
    "-f",
    "--feed",
    multiple=True,
    type=click.STRING,
    help=(
        "Name of a specific feed to remove posts from. To remove from multiple feeds,"
        " use this option before every feed name."
    ),
)
@click.option("-y", "--noconfirm", is_flag=True, help="Skip confirmation prompts")
def remove(post_uri: tuple[str, ...], feed: tuple[str, ...], noconfirm: bool):
    """
    Remove posts from all feeds

    POST_URI is 1 or more bsky.app URLs of the post(s) to remove
    \f

    :param post_uri: `tuple` of bsky.app URLs of posts to remove
    :param feed: `tuple` of feed names to remove posts from, can be empty if `-f/--feed`
        option is not used
    :param noconfirm: Whether to skip confirmation prompts or not
    """
    feed_ids = set(_get_feed_row_by_name_or_abort(feedname).id for feedname in feed)

    post_uris = set(post_uri)
    tids: set[str] = set()
    for uri in post_uris:
        tids.add(_get_post_tid_or_abort(uri))

    query: ModelSelect = Post.select()
    for tid in tids:
        query = query.orwhere(Post.uri.endswith(f"/{tid}"))

    post_ids = set(post.id for post in query)
    if not post_ids:
        _echo_and_abort("No matching posts found in database")

    feed_post_through: Model = Post.feeds.get_through_model()
    query = feed_post_through.select().where(feed_post_through.post_id.in_(post_ids))
    if feed_ids:
        query = query.where(feed_post_through.feed_id.in_(feed_ids))

    num_posts_in_feeds = len(set(row.post_id for row in query))
    ids_to_delete = set(row.id for row in query)

    uri_count = len(post_uris)
    click.echo(
        f"{len(post_ids)}/{uri_count} post{'' if uri_count == 1 else 's'} found in"
        f" database, {num_posts_in_feeds} of them are in feeds."
    )

    if num_posts_in_feeds < 1:
        click.secho("Nothing to do here", fg="green", bold=True)
        return

    if noconfirm or click.confirm(
        f"Remove {num_posts_in_feeds} post{'' if num_posts_in_feeds == 1 else 's'} from"
        " all feeds in database?",
        abort=True,
    ):
        # FIXME: Ask to retry query if DB is locked
        feed_post_through.delete().where(
            feed_post_through.id.in_(ids_to_delete)
        ).execute()
        click.secho("All done! Posts removed successfully", fg="green", bold=True)


if __name__ == "__main__":
    cli()
