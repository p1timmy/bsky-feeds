import logging
from typing import Any

from atproto import models
from click import style

from server.post_utils import get_post_labels, get_post_texts

_EMBED_TYPES = {
    models.AppBskyEmbedImages.Main: "image",
    models.AppBskyEmbedVideo.Main: "video",
    models.AppBskyEmbedExternal.Main: "link",
    models.AppBskyEmbedRecord.Main: "quote",
    models.AppBskyEmbedRecordWithMedia.Main: "media+quote",
}

logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def log_post(
    post: dict,
    header: str,
    logger: logging.Logger = logger,
    level: int = logging.INFO,
    include_media=True,
    extra_fields: dict[str, Any] | None = None,
):
    """
    Make a log entry with nicely formatted post details and texts.

    Each piece of text found in a post is printed on each line, main post text first,
    newlines contained in each text shows up as a blue Enter symbol (`↵`). If no text
    was found (such as in a media post without alt or main texts), a blue `<no text>` is
    printed instead.

    :param logger: a `logging.Logger` instance, defaults to `logging.getLogger("server")`
    :param post: `dict` containing at least the following key/value pairs:

        - `url`: `at://` URI string

        - `record`: `app.bsky.feed.post#Record` model instance

    :param header: Text to display before post details
    :param level: logging level from 0 to 50, defaults to `logging.INFO` (20)
    :param include_media: If True (default), also add video/image/Tenor GIF/KLIPY GIF
        alt texts on each line
    :param extra_fields: (optional) `dict` containing extra info alongside post details
    """
    record: models.AppBskyFeedPost.Record = post["record"]

    # Post details + extra fields
    labels = get_post_labels(post)
    fields: dict[str, Any] = {
        "created_at": record.created_at,
        "uri": post["uri"],
        "embed": _EMBED_TYPES.get(type(record.embed)),
        "is_reply": record.reply is not None,
        "labels": ",".join(labels) or None,
        "lang": ",".join(record.langs) if record.langs is not None else None,
    }
    if extra_fields:
        fields.update(**extra_fields)

    details_str = ""
    for key, val in fields.items():
        details_str += f"[{key}={val}]"

    # Post text and any alt texts if there is an embed
    all_texts = [
        f"  {text.replace('\n', style('↵', fg='blue')).replace('\r', '').strip()}"
        for text in get_post_texts(post, include_media)
    ]
    if all_texts:
        texts_str = "\n".join(all_texts)
    else:
        texts_str = style("  <no text>", fg="blue")

    logger.log(level, "%s %s\n%s", header, details_str, texts_str)
