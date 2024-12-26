import signal
import sys
import threading

from click import style
from flask import Flask, Response, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from server import config, data_stream
from server.algos import MalformedCursorError, algos
from server.data_filter import labels_message_callback, operations_callback
from server.database import Feed, db
from server.logger import logger


def firehose_setup():
    """
    Starts firehose client (data stream) threads and creates database entries for each
    new feed URI.

    This must be called before starting the WSGI server, otherwise no new posts will be
    added to feeds.
    """

    # Add feed URIs if not in database
    with db.atomic():
        for feed_uri in algos:
            Feed.get_or_create(uri=feed_uri)

    stream_stop_event = threading.Event()
    stream_run_args = {
        "service_did": config.SERVICE_DID,
        "stream_stop_event": stream_stop_event,
    }
    repo_stream_thread = threading.Thread(
        target=data_stream.run,
        name="ReposFirehoseClientThread",
        kwargs={**stream_run_args, "on_message_callback": operations_callback},
    )
    labels_stream_thread = threading.Thread(
        target=data_stream.run,
        name="LabelsFirehoseClientThread",
        kwargs={
            **stream_run_args,
            "on_message_callback": labels_message_callback,
            "labels": True,
        },
    )
    repo_stream_thread.start()
    labels_stream_thread.start()

    def stop_stream_threads(*_):
        if not stream_stop_event.is_set():
            logger.info(
                style(
                    "Stopping firehose data streams... Press CTRL+C to force stop them",
                    fg="yellow",
                )
            )
            stream_stop_event.set()

        sys.exit(0)

    signal.signal(signal.SIGINT, stop_stream_threads)

    # Used by hupper to reload the server
    signal.signal(signal.SIGTERM, stop_stream_threads)


app = Flask(__name__, static_folder=None)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


@app.route("/")
def index():
    return (
        "ATProto Feed Generator powered by The AT Protocol SDK for Python"
        " (https://github.com/MarshalX/atproto)."
    )


@app.route("/.well-known/did.json", methods=["GET"])
def did_json() -> tuple[str, int] | Response:
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
def describe_feed_generator() -> Response:
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
def get_feed_skeleton() -> tuple[str, int] | Response:
    feed = request.args.get("feed", default=None, type=str)
    algo = algos.get(feed)
    if not algo:
        return "Unsupported algorithm", 400

    try:
        cursor = request.args.get("cursor", default=None, type=str)
        limit = request.args.get("limit", default=20, type=int)
        body = algo(cursor, limit, feed)
    except MalformedCursorError:
        return "Malformed cursor", 400  # noqa: CLB100

    return jsonify(body)
