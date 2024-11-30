import peewee

db = peewee.SqliteDatabase("feed_database.db")


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Post(BaseModel):
    uri = peewee.CharField(index=True)
    cid = peewee.CharField()
    author_did = peewee.CharField()
    reply_parent = peewee.CharField(null=True, default=None)
    reply_root = peewee.CharField(null=True, default=None)
    indexed_at = peewee.TimestampField(null=False, resolution=3, utc=True)


class Feed(BaseModel):
    uri = peewee.CharField(unique=True)
    posts = peewee.ManyToManyField(Post, backref="feeds")


class SubscriptionState(BaseModel):
    service = peewee.CharField(unique=True)
    cursor = peewee.BigIntegerField()


if db.is_closed():
    db.connect()
    db.create_tables([Post, Feed, Feed.posts.get_through_model(), SubscriptionState])
