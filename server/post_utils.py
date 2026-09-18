import re
from typing import Any

from atproto import models
from atproto_client.models.dot_dict import DotDict

TWEET_URL_RE = re.compile(r"^https?://(x|twitter).com/\w+/status/[0-9]+.*$")
YOUTUBE_URL_RE = re.compile(r"^https?://(([a-z]+\.)?youtube\.com|youtu\.be)/.+$")
GIF_URL_BASES = ("https://media.tenor.com/", "https://static.klipy.com/")

PostRecordType = models.AppBskyFeedPost.Record | DotDict


def post_has_media_embeds(record: PostRecordType) -> bool:
    """
    Check if a post contains media (image/video/Tenor GIF/KLIPY GIF) embeds. Posts with
    link embeds pointing to other external media (YouTube/Spotify/etc.) don't count.

    :param record: `app.bsky.feed.post#Record` model object containing post data.
    """
    embed = record.embed
    if isinstance(embed, models.AppBskyEmbedRecordWithMedia.Main):
        embed = embed.media

    return isinstance(
        embed,
        (models.AppBskyEmbedImages.Main, models.AppBskyEmbedVideo.Main),
    ) or (
        isinstance(embed, models.AppBskyEmbedExternal.Main)
        and embed.external.uri.startswith(GIF_URL_BASES)
    )


def get_post_texts(record: PostRecordType, include_media=True) -> list[str]:
    """
    Extract text content from a single post.

    :param record: `app.bsky.feed.post#Record` model object containing post data.
    :param include_media: Also get image/video/Tenor GIF/KLIPY GIF alt texts and link
        embed titles and descriptions (only for YouTube and 𝕏/Twitter) in addition to
        the post text.
        Defaults to True.
    """
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
            if link.uri.startswith(GIF_URL_BASES) and link.description:
                # Tenor/KLIPY GIFs inserted using the post editor use link embeds,
                # official Bluesky app lets you add custom alt text which is put into
                # description field in embed
                texts.append(link.description)
            elif YOUTUBE_URL_RE.search(link.uri):
                texts.append(link.title)
                if link.description:
                    texts.append(link.description)
            elif TWEET_URL_RE.search(link.uri) and link.description:
                texts.append(link.description)

    return texts


def get_post_labels(record: PostRecordType) -> list[str]:
    """
    Get a flattened `list` of post label values.

    :param record: `app.bsky.feed.post#Record` model object containing post data.
    """
    if record.labels is None:
        return []
    elif isinstance(record.labels, DotDict):
        if record.py_type != models.ids.AppBskyFeedPost:
            raise TypeError("can only get labels from app.bsky.feed.post records")

        # Some posts have `DotDict` objects instead of the expected model for
        # `com.atproto.label.defs#selfLabels`, the fact `DotDict` already has a
        # `values` method prevents access to "values" key through attrs
        labels_dict = record.labels.to_dict()
        return [value.get("val", {}) for value in labels_dict.get("values", [])]

    return [value.val for value in record.labels.values]
