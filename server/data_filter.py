import logging
from collections import defaultdict
from collections.abc import Iterable

from atproto import models
from click import style

from server.algos import filters
from server.database import Feed, Post, db

_PR0N_LABEL = models.ComAtprotoLabelDefs.SelfLabel(val="porn")
_ADULT_LABELS = ("porn", "nudity", "sexual")
_BSKY_MOD_SERVICE = "did:plc:ar7c4by46qjdydhdevvrndac"

logger = logging.getLogger(__name__)

# Store feed rows from DB to memory to save on queries
_all_feeds: dict[str, Feed] = {}
for row in Feed.select():
    _all_feeds[row.uri] = row


def operations_callback(ops: defaultdict):
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync
    posts_to_create: list[dict] = []
    created_post: dict
    for created_post in ops[models.ids.AppBskyFeedPost]["created"]:
        author: str = created_post["author"]
        record: models.AppBskyFeedPost.Record = created_post["record"]

        # Hide post if it has adult content (porn) label
        pr0n_post_count = 0
        has_pr0n_label = False
        if (
            record.labels
            and record.labels.values is not None
            and _PR0N_LABEL in record.labels.values
        ):
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

            if has_pr0n_label:
                pr0n_post_count += 1

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
        with db.atomic():
            for post_dict in posts_to_create:
                feeds = post_dict.pop("feeds")
                p = Post.create(**post_dict)
                if feeds:
                    p.feeds.add(feeds)

        new_post_count = len(posts_to_create) - pr0n_post_count
        if new_post_count > 0:
            logger.info(style("Posts added to feeds: %s", fg="green"), new_post_count)


def labels_message_callback(
    labels_message: models.ComAtprotoLabelSubscribeLabels.Labels,
):
    posts_to_update: list[Post] = []
    hide_count = unhide_count = 0

    for label in labels_message.labels:
        if (
            "/app.bsky.feed.post/" not in label.uri  # posts only
            or label.src != _BSKY_MOD_SERVICE  # labels by Bluesky Moderation Service
            or label.val not in _ADULT_LABELS  # pr0n/nudity/sexual labels only
        ):
            continue

        post = Post.get_or_none(Post.uri == label.uri)
        if not post:
            continue

        old_value = post.adult_labels
        flag_name = f"has_{label.val}_label"
        if getattr(post, flag_name, None) is not None:
            setattr(post, flag_name, not label.neg)
            posts_to_update.append(post)
            logger.debug(
                style("[%s] %s: %03b -> %03b", fg="magenta", dim=True),
                post.id,
                post.uri,
                old_value,
                post.adult_labels,
            )

        if not old_value:
            hide_count += 1
        elif not post.adult_labels:
            unhide_count += 1

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
