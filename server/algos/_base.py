from datetime import UTC, datetime, timedelta
from typing import Optional

from atproto import models
from multiformats_cid import is_cid
from peewee import ModelSelect

from server.database import Feed, Post

FORTNIGHT = timedelta(days=14)
CURSOR_EOF = "eof"


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
