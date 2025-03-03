import signal
import sys
import threading

import validators
from click import style
from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.proxy_fix import ProxyFix

from server import config, data_stream
from server.algos import MalformedCursorError, algo_names, algos, userlists
from server.data_filter import labels_message_callback, operations_callback
from server.database import Feed, db
from server.logger import logger
from server.scheduler import setup_scheduler, update_user_lists


def firehose_setup(do_userlist_updates: bool = False):
    """
    Starts firehose client (data stream) threads and background user list updates
    scheduler. Also creates database entries for each new feed URI.

    This must be called before starting the WSGI server, otherwise no new posts will be
    added to feeds.
    """

    # Add feed URIs if not in database
    with db.atomic():
        for feed_uri, algo_name in algo_names.items():
            feed: Feed
            _: bool
            feed, _ = Feed.get_or_create(uri=feed_uri)

            # Set algo_name separately in case DB was just migrated
            if not feed.algo_name:
                Feed.update(algo_name=algo_name).where(Feed.uri == feed_uri).execute()

    # Warn if handle is invalid or login credentials missing/unset
    no_list_auto_update_reason = ""
    if config.HANDLE:
        if validators.domain(config.HANDLE) is not True:
            no_list_auto_update_reason = '"HANDLE" is not a valid Bluesky handle'
        elif not config.PASSWORD:
            no_list_auto_update_reason = (
                '"PASSWORD" environment variable is missing or left blank'
            )
        elif all(not userlist.uri for userlist in userlists):
            # FIXME: Different message if URIs of all userlists are hardcoded to None
            no_list_auto_update_reason = "No list URIs found in config"
    else:
        no_list_auto_update_reason = (
            '"HANDLE" environment variable is missing or left blank'
        )

    if no_list_auto_update_reason:
        do_userlist_updates = False
        logger.warning(
            style(
                "%s, lists won't be updated until next server restart",
                fg="yellow",
            ),
            no_list_auto_update_reason,
        )

    # Check for user list updates if `--update-lists-now` flag is used
    if do_userlist_updates:
        logger.info("Checking for user list updates...")
        update_user_lists(userlists)

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
    scheduler = setup_scheduler(not no_list_auto_update_reason)

    repo_stream_thread.start()
    labels_stream_thread.start()

    if scheduler:
        scheduler.start()

    def stop_stream_threads(*_):
        if not stream_stop_event.is_set():
            logger.info(
                style(
                    "Stopping firehose data streams... Press CTRL+C to force stop them",
                    fg="yellow",
                )
            )
            stream_stop_event.set()

            if scheduler:
                scheduler.shutdown(wait=False)

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
        raise NotFound()

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


# Make all generic errors return just the name instead of a webpage for response body.
# Routes should use `return "[message]", [error code]` to display a custom message.
@app.errorhandler(HTTPException)
def generic_error(e: HTTPException) -> tuple[str, int]:
    return e.name, e.code


# No response body for 404 Not Found errors
@app.errorhandler(NotFound)
def not_found_error(_) -> tuple[str, int]:
    return "", 404
