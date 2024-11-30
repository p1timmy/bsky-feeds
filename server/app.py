import signal
import sys
import threading

from click import style
from flask import Flask, jsonify, request

from server import config, data_stream
from server.algos import algos
from server.data_filter import operations_callback
from server.database import Feed, db
from server.logger import logger

app = Flask(__name__)

stream_stop_event = threading.Event()
stream_thread = threading.Thread(
    target=data_stream.run,
    args=(
        config.SERVICE_DID,
        operations_callback,
        stream_stop_event,
    ),
)
stream_thread.start()


def sigint_handler(*_):
    logger.info(style("Stopping data stream...", fg="yellow"))
    stream_stop_event.set()
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)


# Add feed URIs if not in database
with db.atomic():
    for feed_uri in algos:
        Feed.get_or_create(uri=feed_uri)


@app.route("/")
def index():
    return (
        "ATProto Feed Generator powered by The AT Protocol SDK for Python"
        " (https://github.com/MarshalX/atproto)."
    )


@app.route("/.well-known/did.json", methods=["GET"])
def did_json():
    if not config.SERVICE_DID.endswith(config.HOSTNAME):
        return "", 404

    return jsonify(
        {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": config.SERVICE_DID,
            "service": [
                {
                    "id": "#bsky_fg",
                    "type": "BskyFeedGenerator",
                    "serviceEndpoint": f"https://{config.HOSTNAME}",
                }
            ],
        }
    )


@app.route("/xrpc/app.bsky.feed.describeFeedGenerator", methods=["GET"])
def describe_feed_generator():
    feeds = [{"uri": uri} for uri in algos.keys()]
    response = {
        "encoding": "application/json",
        "body": {
            "did": config.SERVICE_DID,
            "feeds": feeds,
        },
    }
    return jsonify(response)


@app.route("/xrpc/app.bsky.feed.getFeedSkeleton", methods=["GET"])
def get_feed_skeleton():
    feed = request.args.get("feed", default=None, type=str)
    algo = algos.get(feed)
    if not algo:
        return "Unsupported algorithm", 400

    try:
        cursor = request.args.get("cursor", default=None, type=str)
        limit = request.args.get("limit", default=20, type=int)
        body = algo(cursor, limit, feed)
    except ValueError as e:
        exc_msg = str(e)
        if exc_msg.lower() == "malformed cursor":
            return exc_msg, 400  # noqa: CLB100
        raise e

    return jsonify(body)
