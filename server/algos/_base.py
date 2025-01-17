from datetime import UTC, datetime, timedelta
from typing import Optional

from atproto import models
from multiformats_cid import is_cid
from peewee import ModelSelect

from server.database import Feed, Post

FORTNIGHT = timedelta(days=14)
CURSOR_EOF = "eof"


def get_post_texts(post: dict, include_media=True) -> list[str]:
    """
    Extract text content from a single post.

    :param include_media: Also get image/GIF/video alt texts in addition to the post text.
        Defaults to True.
    """
    record: models.AppBskyFeedPost.Record = post["record"]
    texts: list[str] = []
    if record.text:  # some posts may not have any text at all
        texts.append(record.text)

    # Get alt text from images/video
    embed = record.embed
    if embed and include_media:
        # Post has both pics/video and a quoted post
        if isinstance(embed, models.AppBskyEmbedRecordWithMedia.Main):
            embed = embed.media

        if isinstance(embed, models.AppBskyEmbedImages.Main):
            for image in embed.images:
                if image.alt:
                    texts.append(image.alt)
        elif isinstance(embed, models.AppBskyEmbedVideo.Main) and embed.alt:
            texts.append(embed.alt)
        elif isinstance(embed, models.AppBskyEmbedExternal.Main):
            # Tenor GIFs inserted using the post editor use link embeds, alt text is put
            # into the link description
            link = embed.external
            if link.uri.startswith("https://media.tenor.com/") and link.description:
                texts.append(link.description)

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
