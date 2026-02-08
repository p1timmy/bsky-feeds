import re
from datetime import UTC, datetime, timedelta
from typing import Optional

from atproto import models
from multiformats_cid import is_cid
from peewee import ModelSelect

from server.database import Feed, Post

FORTNIGHT = timedelta(days=14)
CURSOR_EOF = "eof"
TWEET_URL_RE = re.compile(r"^https?://(x|twitter).com/\w+/status/[0-9]+.*$")
YOUTUBE_URL_RE = re.compile(r"^https?://(([a-z]+\.)?youtube\.com|youtu\.be)/.+$")


def post_has_media_embeds(post: dict) -> bool:
    """
    Check if a post contains media (image/video/Tenor GIF) embeds. Posts with link embeds
    pointing to other external media (YouTube/Spotify/etc.) don't count.
    """
    record: models.AppBskyFeedPost.Record = post["record"]
    embed = record.embed
    if isinstance(embed, models.AppBskyEmbedRecordWithMedia.Main):
        embed = embed.media

    return isinstance(
        embed,
        (models.AppBskyEmbedImages.Main, models.AppBskyEmbedVideo.Main),
    ) or (
        isinstance(embed, models.AppBskyEmbedExternal.Main)
        and embed.external
        and embed.external.uri.startswith("https://media.tenor.com/")
    )


def get_post_texts(post: dict, include_media=True) -> list[str]:
    """
    Extract text content from a single post.

    :param post: `dict` containing at least a `record` key with `app.bsky.feed.post#Record`
        model instance value
    :param include_media: Also get image/video/Tenor GIF alt texts and link embed titles
        and descriptions (only for YouTube and 𝕏/Twitter) in addition to the post text.
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
            link = embed.external
            if link.uri.startswith("https://media.tenor.com/") and link.description:
                # Tenor GIFs inserted using the post editor use link embeds, official
                # Bluesky app lets you add custom alt text which is put into description
                # field in embed
                texts.append(link.description)
            elif YOUTUBE_URL_RE.search(link.uri) or TWEET_URL_RE.search(link.uri):
                texts.append(link.title)
                if link.description:
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
