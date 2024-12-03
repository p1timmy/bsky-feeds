from datetime import datetime
from typing import Optional

from atproto_client.models.app.bsky.embed.images import Image
from atproto_client.models.app.bsky.embed.images import Main as ImageEmbed
from atproto_client.models.app.bsky.feed.post import Record
from peewee import ModelSelect

from server.database import Feed, Post

CURSOR_EOF = "eof"


# TODO: scan link URLs/embeds
def get_post_texts(post: dict, include_images=True) -> list[str]:
    """
    Extract text content from a single post.

    :param include_images: Also get image/video alt texts in addition to the post text.
        Defaults to True.
    """
    record: Record = post["record"]
    texts: list[str] = []
    if record.text:  # some posts may not have any text at all
        texts.append(record.text)

    # Get alt text from images
    if include_images and record.embed:
        imagelist: Optional[ImageEmbed] = getattr(record.embed, "images", None)
        if imagelist:
            image: Image
            for image in imagelist:
                if image.alt:
                    texts.append(image.alt)

    return texts


class MalformedCursorError(ValueError):
    """`cursor` parameter from request URL doesn't follow the `timestamp::cid` format"""


def handler(cursor: Optional[str], limit: int, feed_uri: str) -> dict:
    """
    Handler for generating a feed's skeleton (list of post URIs).

    This retrieves all posts in database that are only linked to the given `feed_uri` in
    strict reverse chronological order (newest to oldest).
    """
    posts: ModelSelect = (
        Post.select()
        .join(Feed.posts.get_through_model())
        .join(Feed)
        .where(Feed.uri == feed_uri)
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

        # TODO: Validate `cid` format
        indexed_at, cid = cursor_parts
        try:
            indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
        except ValueError:
            # `indexed_at` (timestamp) value isn't an int
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
