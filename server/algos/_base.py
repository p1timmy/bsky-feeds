import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePath
from typing import Optional

from atproto_client.models.app.bsky.embed.images import Image
from atproto_client.models.app.bsky.embed.images import Main as ImageEmbed
from atproto_client.models.app.bsky.embed.record_with_media import (
    Main as MediaAndQuoteEmbed,
)
from atproto_client.models.app.bsky.embed.video import Main as VideoEmbed
from atproto_client.models.app.bsky.feed.post import Record
from click import style
from multiformats_cid import is_cid
from peewee import ModelSelect

from server.database import Feed, Post
from server.logger import logger

FORTNIGHT = timedelta(days=14)
CURSOR_EOF = "eof"


def load_user_list(filename: str, user_set: set[str]):
    """
    Load a list of user DIDs from a CSV file in the `lists` directory

    :param filename: Name of the CSV file to load
    :param user_set: `set` instance where DIDs will be added into

    :raises KeyError: If the CSV file is missing a `did` column
    """
    module_dir = PurePath(__file__).parent
    user_list_path = Path(*module_dir.parts[:-2], "lists", filename)
    with user_list_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_did = row["did"]

            # TODO: check if it's a valid DID
            if user_did.startswith("did:"):
                user_set.add(user_did)


def load_user_list_with_logs(filename: str, user_set: set[str], list_desc: str):
    """
    Same as `load_user_list` but with log entries added for use while running the feed
    generator server

    :param filename: Name of the CSV file to load
    :param user_set: `set` instance where DIDs will be added into
    :param list_desc: Description of the list being loaded, to be shown in logs
    """
    initial_count = len(user_set)
    try:
        load_user_list(filename, user_set)
    except Exception:  # noqa: PIE786
        logger.warning(
            style("Failed to load %s", fg="yellow", bold=True), list_desc, exc_info=True
        )
    else:
        added_count = len(user_set) - initial_count
        if added_count > 0:
            logger.debug("Loaded DIDs in %s: %d", list_desc, added_count)


# TODO: scan link URLs/embeds
def get_post_texts(post: dict, include_media=True) -> list[str]:
    """
    Extract text content from a single post.

    :param include_media: Also get image/video alt texts in addition to the post text.
        Defaults to True.
    """
    record: Record = post["record"]
    texts: list[str] = []
    if record.text:  # some posts may not have any text at all
        texts.append(record.text)

    # Get alt text from images/video
    embed = record.embed
    if include_media:
        # Post has both pics/video and a quoted post
        if isinstance(embed, MediaAndQuoteEmbed):
            embed = embed.media

        if isinstance(embed, ImageEmbed):
            image: Image
            for image in embed.images:
                if image.alt:
                    texts.append(image.alt)
        elif isinstance(embed, VideoEmbed) and embed.alt:
            texts.append(embed.alt)

    return texts


class MalformedCursorError(ValueError):
    """`cursor` parameter from request URL doesn't follow the `timestamp::cid` format"""


def handler(cursor: Optional[str], limit: int, feed_uri: str) -> dict:
    """
    Handler for generating a feed's skeleton (list of post URIs).

    This retrieves all posts in database that are only linked to the given `feed_uri` in
    strict reverse chronological order (newest to oldest).
    """
    datetime_14d_ago = datetime.now(UTC) - FORTNIGHT
    posts: ModelSelect = (
        Post.select()
        .join(Feed.posts.get_through_model())
        .join(Feed)
        .where(Feed.uri == feed_uri)
        .where(Post.adult_labels == 0)
        .where(Post.indexed_at > datetime_14d_ago)
        .order_by(Post.cid.desc())
        .order_by(Post.indexed_at.desc())
        .limit(limit)
    )

    if cursor:
        if cursor == CURSOR_EOF:
            return {
                "cursor": CURSOR_EOF,
                "feed": [],
            }

        cursor_parts = cursor.split("::")
        if len(cursor_parts) != 2:
            raise MalformedCursorError()

        indexed_at, cid = cursor_parts
        try:
            indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
        except ValueError:
            # `indexed_at` (timestamp) value isn't an int
            raise MalformedCursorError()

        if not is_cid(cid):
            raise MalformedCursorError()

        posts = posts.where(
            ((Post.indexed_at == indexed_at) & (Post.cid < cid))
            | (Post.indexed_at < indexed_at)
        )

    feed = [{"post": post.uri} for post in posts]

    cursor = CURSOR_EOF
    if posts:
        last_post: Post = posts[-1]
        cursor = f"{int(last_post.indexed_at.timestamp() * 1000)}::{last_post.cid}"

    return {
        "cursor": cursor,
        "feed": feed,
    }
