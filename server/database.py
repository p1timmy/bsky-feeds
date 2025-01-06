import atexit
from enum import IntEnum

import peewee
from playhouse import migrate

from server import config

db = peewee.SqliteDatabase(
    "feed_database.db",
    pragmas={
        "main.journal_mode": "WAL",
        "main.synchronous": "NORMAL",
        "main.journal_size_limit": config.DB_JOURNAL_SIZE_LIMIT,
        "main.mmap_size": config.DB_MMAP_SIZE,
        "main.cache_size": config.DB_CACHE_SIZE,
        "main.wal_autocheckpoint": config.DB_WAL_AUTOCHECKPOINT,
    },
)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField(unique=True)
    author_did = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.TimestampField(null=False, resolution=3, utc=True)
    adult_labels = peewee.BitField(null=False, default=0)

    has_porn_label = adult_labels.flag(0b0001)
    has_nudity_label = adult_labels.flag(0b0010)
    has_sexual_label = adult_labels.flag(0b0100)
    has_sexual_figurative_label = adult_labels.flag(0b1000)


class Feed(BaseModel):
    uri = peewee.CharField(unique=True)
    posts = peewee.ManyToManyField(Post, backref="feeds")


class FirehoseType(IntEnum):
    REPOS = 0
    LABELS = 1


class SubscriptionState(BaseModel):
    service = peewee.CharField()
    cursor = peewee.BigIntegerField()
    firehose_type = peewee.IntegerField(
        null=False,
        default=FirehoseType.REPOS,
        choices=[(t.value, t.name.lower()) for t in FirehoseType],
    )

    class Meta:
        indexes = [
            # Cursor is unique per firehose type per service
            (("service", "firehose_type"), True),
        ]
        database = db


def _close_db_at_exit():
    if not db.is_closed():
        db.close()


atexit.register(_close_db_at_exit)

if db.is_closed():
    db.connect()
    if not db.get_tables():
        db.create_tables(
            [Post, Feed, Feed.posts.get_through_model(), SubscriptionState], safe=True
        )

    migrator = migrate.SqliteMigrator(db)
    migrations: list[list] = []

    tablename = "post"
    post_cols = [col.name for col in db.get_columns(tablename)]
    if "adult_labels" not in post_cols:
        migrations.append(
            migrator.add_column(tablename, "adult_labels", Post.adult_labels)
        )

    tablename = "subscriptionstate"
    subscription_state_cols = [col.name for col in db.get_columns(tablename)]
    if "firehose_type" not in subscription_state_cols:
        migrations.extend(
            [
                migrator.add_column(
                    tablename, "firehose_type", SubscriptionState.firehose_type
                ),
                migrator.drop_index(tablename, "subscriptionstate_service"),
                migrator.add_index(
                    tablename, ("service", "firehose_type"), unique=True
                ),
            ]
        )

    if migrations:
        with db.atomic():
            migrate.migrate(*migrations)
            db.pragma("main.user_version", 2)
