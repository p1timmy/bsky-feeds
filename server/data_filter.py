import logging
from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import NamedTuple, Optional, Self

from atproto import models
from click import style
from peewee import IntegrityError

from server import data_stream
from server.algos import filters
from server.database import Feed, Post, db

_PR0N_LABEL = models.ComAtprotoLabelDefs.SelfLabel(val="porn")
_ADULT_LABELS = ("porn", "nudity", "sexual", "sexual-figurative")
_BSKY_MOD_SERVICE = "did:plc:ar7c4by46qjdydhdevvrndac"
_MAX_COMMIT_LAG = timedelta(seconds=0.25)
_ARCHIVED_THRESHOLD = timedelta(days=1)

logger = logging.getLogger(__name__)

# Store feed rows from DB to memory to save on queries
_all_feeds: dict[str, Feed] = {}
for row in Feed.select():
    _all_feeds[row.uri] = row


def post_has_pr0n_label(post: dict) -> bool:
    """
    Check if a post was published with a porn (explicit adult content) label added by
    the author
    """
    record: models.AppBskyFeedPost.Record = post["record"]
    return (
        record.labels
        and record.labels.values is not None
        and _PR0N_LABEL in record.labels.values
    )


def is_archived_post(post: dict) -> bool:
    """
    Check if a post is an archived one, meaning post creation date is over 24 hours old
    as indicated by the official Bluesky app

    (See
    https://github.com/bluesky-social/social-app/blob/6471e809aa28f0319bde4aa1f362679e3723d298/src/view/com/post-thread/PostThreadItem.tsx#L779)
    """
    created_at = datetime.fromisoformat(post["record"].created_at)
    published_at: datetime = post["time"]
    return published_at - created_at > _ARCHIVED_THRESHOLD


def operations_callback(ops: defaultdict):
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync
    posts_to_create: list[dict] = []
    created_post: dict
    for created_post in ops[models.ids.AppBskyFeedPost]["created"]:
        author: str = created_post["author"]
        record: models.AppBskyFeedPost.Record = created_post["record"]

        # Skip archived posts (mostly those imported from 𝕏/Twitter or similar)
        if is_archived_post(created_post):
            continue

        # Hide post if it has adult content (porn) label
        has_pr0n_label = False
        if post_has_pr0n_label(created_post):
            has_pr0n_label = True

        feeds: list[Feed] = []
        for algo_uri, filter in filters.items():
            if filter(created_post):
                feed_row = _all_feeds.get(algo_uri)
                if feed_row:
                    feeds.append(feed_row)

        if feeds:
            # print post to show that it will be added to feeds
            post_has_embeds = isinstance(
                record.embed,
                (models.AppBskyEmbedImages.Main, models.AppBskyEmbedVideo.Main),
            )
            inlined_text = record.text.replace("\n", " ").strip() or "<no text>"
            post_is_reply = bool(record.reply)
            logger.info(
                "NEW POST "
                "[created_at=%s]"
                "[author=%s]"
                "[with_embed=%s]"
                "[is_reply=%s]"
                "[feed_uris=%s]"
                ": %s",
                record.created_at,
                author,
                post_has_embeds,
                post_is_reply,
                [feed.uri for feed in feeds],
                inlined_text,
            )
            logger.debug(created_post)

            reply_root = reply_parent = None
            if post_is_reply:
                reply_root = record.reply.root.uri
                reply_parent = record.reply.parent.uri

            post_dict = {
                "uri": created_post["uri"],
                "cid": created_post["cid"],
                "author_did": author,
                "reply_parent": reply_parent,
                "reply_root": reply_root,
                "has_porn_label": has_pr0n_label,
                "feeds": feeds,
            }
            posts_to_create.append(post_dict)

    posts_to_delete: Iterable[dict] = ops[models.ids.AppBskyFeedPost]["deleted"]
    if posts_to_delete:
        uris: list[str] = [post["uri"] for post in posts_to_delete]
        query = Post.uri.in_(uris)
        count: int = Post.select().where(query).count()
        if count:
            with db.atomic():
                Post.delete().where(query)

            logger.info(style("Posts deleted from feeds: %s", fg="red"), count)

    if posts_to_create:
        new_post_count = 0
        with db.atomic():
            for post_dict in posts_to_create:
                feeds = post_dict.pop("feeds")
                try:
                    post = Post.create(**post_dict)
                except IntegrityError as e:
                    # If caused by unique constraint on `cid` column, that means post
                    # was already added to DB
                    if e.args:
                        message = e.args[0]
                        if message.startswith(
                            "UNIQUE constraint failed"
                        ) and message.endswith(".cid"):
                            logger.debug(
                                style(
                                    "Post already exists in database",
                                    fg="red",
                                    dim=True,
                                )
                            )
                            continue

                    raise e
                else:
                    post.feeds.add(feeds)
                    if not post.has_porn_label:
                        new_post_count += 1

        if new_post_count > 0:
            logger.info(style("Posts added to feeds: %s", fg="green"), new_post_count)


class _LabelQueueItem(NamedTuple):
    time: datetime
    label: models.ComAtprotoLabelDefs.Label
    cursor: int

    @classmethod
    def from_label(cls, label: models.ComAtprotoLabelDefs.Label, cursor: int) -> Self:
        cts_dt = datetime.fromisoformat(label.cts)
        return cls(cts_dt, label, cursor)


_label_queue: deque[_LabelQueueItem] = deque([])


def labels_message_callback(
    labels_message: models.ComAtprotoLabelSubscribeLabels.Labels,
) -> int:
    # Add headroom as label timestamps are always behind by fraction of a second due to
    # network lag
    repos_last_message_time = data_stream.repos_last_message_time + _MAX_COMMIT_LAG
    queue_initial_size = len(_label_queue)

    for label in labels_message.labels:
        if (
            "/app.bsky.feed.post/" in label.uri  # posts only
            and label.src == _BSKY_MOD_SERVICE  # labels by Bluesky Moderation Service
            and label.val in _ADULT_LABELS  # pr0n/nudity/sexual labels only
        ):
            _label_queue.append(_LabelQueueItem.from_label(label, labels_message.seq))

    posts_to_update: list[Post] = []
    hide_count = unhide_count = 0

    # Process labels whose timestamps are older than that of last received repos commit
    while _label_queue and _label_queue[0].time < repos_last_message_time:
        label = _label_queue.popleft().label
        post: Optional[Post] = Post.get_or_none(Post.uri == label.uri)
        if not post:
            continue

        label_name = label.val.replace("-", "_")
        flag_name = f"has_{label_name}_label"
        if getattr(post, flag_name, None) is None:
            continue

        old_value: int = post.adult_labels
        setattr(post, flag_name, not label.neg)
        posts_to_update.append(post)
        logger.debug(
            style(
                "Updating adult label flags for %s (%s): %s -> %s",
                fg="magenta",
                dim=True,
            ),
            post.uri,
            post.id,
            format(old_value, "#06b"),
            format(post.adult_labels, "#06b"),
        )
        logger.debug(label)

        if not old_value:
            hide_count += 1
        elif not post.adult_labels:
            unhide_count += 1

    queue_size_change = len(_label_queue) - queue_initial_size
    if queue_size_change < 0:
        logger.debug(
            style("Processed %s label%s waiting in queue", dim=True),
            abs(queue_size_change),
            "" if queue_size_change == -1 else "s",
        )

    if posts_to_update:
        with db.atomic():
            Post.bulk_update(posts_to_update, [Post.adult_labels])

    if hide_count:
        logger.info(
            style("Posts hidden from feeds due to added labels: %d", fg="magenta"),
            hide_count,
        )

    if unhide_count:
        logger.info(
            style("Posts restored to feeds due to removed labels: %d", fg="cyan"),
            unhide_count,
        )

    # If there are still labels left waiting in queue, return cursor number from 1st
    # item in case the queue disappears after shutdown
    if _label_queue:
        return _label_queue[0].cursor

    return labels_message.seq
