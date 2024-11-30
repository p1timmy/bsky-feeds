import logging
from collections import defaultdict
from collections.abc import Iterable

from atproto import models
from atproto_client.models.app.bsky.feed.post import Record
from click import style

from server.algos import filters
from server.database import Feed, Post, db

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
        record: Record = created_post["record"]

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
        with db.atomic():
            for post_dict in posts_to_create:
                feeds = post_dict.pop("feeds")
                p = Post.create(**post_dict)
                if feeds:
                    p.feeds.add(feeds)

        logger.info(style("Posts added to feeds: %s", fg="green"), len(posts_to_create))
