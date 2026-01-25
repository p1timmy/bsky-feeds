from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event
from time import sleep
from typing import Any, Optional

from atproto import (
    CAR,
    AtUri,
    FirehoseSubscribeLabelsClient,
    FirehoseSubscribeReposClient,
    firehose_models,
    models,
    parse_subscribe_labels_message,
    parse_subscribe_repos_message,
)
from atproto.exceptions import FirehoseError
from atproto_client.models.dot_dict import DotDict
from atproto_firehose.firehose import SubscribeLabelsMessage, SubscribeReposMessage
from click import style

from server.database import FirehoseType, SubscriptionState
from server.logger import logger

_INTERESTED_RECORDS = {
    models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
}
_ReposOperationsCallbackType = Callable[[dict[str, Any]], None]
_LabelsMessageCallbackType = Callable[
    [models.ComAtprotoLabelSubscribeLabels.Labels], int
]
repos_last_message_time: datetime = datetime.min.replace(tzinfo=UTC)


def _get_commit_ops_by_type(
    commit: models.ComAtprotoSyncSubscribeRepos.Commit,
) -> defaultdict:
    operation_by_type = defaultdict(lambda: {"created": [], "deleted": []})
    if len(commit.blocks) >= 50_000:
        return operation_by_type

    car = CAR.from_bytes(commit.blocks)
    for op in commit.ops:
        if op.action == "update":
            # we are not interested in updates
            continue

        uri = AtUri.from_str(f"at://{commit.repo}/{op.path}")

        if op.action == "create":
            if not op.cid:
                continue

            record_raw_data = car.blocks.get(op.cid)
            if not record_raw_data:
                continue

            record = models.get_or_create(record_raw_data, strict=False)

            # Drop operation if type is not in ATProto/Bluesky lexicon to prevent log
            # spamming and other unexpected weird stuff
            if record is None or isinstance(record, DotDict):
                continue

            for record_type, record_nsid in _INTERESTED_RECORDS.items():
                if uri.collection == record_nsid and models.is_record_type(
                    record, record_type
                ):
                    operation_by_type[record_nsid]["created"].append(
                        {
                            # Object containing all the details of the record
                            "record": record,
                            # ATProto URI of the record
                            # (hint: for posts use https://hopper.at/ to get its
                            # regular link)
                            "uri": str(uri),
                            # Unique identifier of a record, used by `cursor` parameter
                            # in feed URLs
                            "cid": str(op.cid),
                            # DID of account that made the record
                            "author": commit.repo,
                            # Date/time of when the record was made.
                            # In the case of posts, it's the real publish date aka the
                            # post date/time as shown in clients
                            "time": datetime.fromisoformat(commit.time),
                        }
                    )
                    break

        if op.action == "delete":
            operation_by_type[uri.collection]["deleted"].append({"uri": str(uri)})

    return operation_by_type


def _get_commit_details_str(commit: models.ComAtprotoSyncSubscribeRepos.Commit):
    ops = "\n".join([f"  - {op.action} {op.path} ({op.cid})" for op in commit.ops])
    return f"\nRepo: {commit.repo}\nOperations:\n{ops}"


def _log_message_error(
    frame: firehose_models.Frame | None = None,
    parsed_data: SubscribeReposMessage | SubscribeLabelsMessage | None = None,
):
    if frame is not None:
        header = style("Failed to process firehose message", fg="red", bold=True)
        if parsed_data is None:
            logger.exception("%s\nBody: %s", header, frame.body)
            return

        if isinstance(parsed_data, models.ComAtprotoSyncSubscribeRepos.Commit):
            commit_info = _get_commit_details_str(parsed_data)
        else:
            commit_info = ""

        logger.exception(
            "%s\nType: %s%s%s",
            header,
            parsed_data.py_type,
            f" @ cursor {parsed_data.seq}" if hasattr(parsed_data, "seq") else "",
            commit_info,
        )
    else:
        logger.exception(
            style("Error in firehose message handler", fg="red", bold=True)
        )


def _run_repos_client(
    service_did: str,
    callback: _ReposOperationsCallbackType,
    stream_stop_event: Optional[Event] = None,
    relay_server: str = "bsky.network",
):
    state = SubscriptionState.get_or_none(
        (SubscriptionState.service == service_did)
        & (SubscriptionState.firehose_type == FirehoseType.REPOS)
    )
    params = None
    last_cursor = 0
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)

    client = FirehoseSubscribeReposClient(params, base_uri=f"wss://{relay_server}/xrpc")

    if not state:
        SubscriptionState.create(
            service=service_did, cursor=0, firehose_type=FirehoseType.REPOS
        )

    frame: firehose_models.Frame | None = None
    msg_data: SubscribeReposMessage | None = None

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        # stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        nonlocal frame, msg_data
        frame = message
        msg_data = parse_subscribe_repos_message(message)

        global repos_last_message_time
        message_ts = datetime.fromisoformat(msg_data.time)
        if message_ts > repos_last_message_time:
            repos_last_message_time = message_ts

        # We no longer need the message unless if it's a commit
        if not isinstance(msg_data, models.ComAtprotoSyncSubscribeRepos.Commit):
            return

        # Update stored state every ~1000 messages in case we get disconnected
        if msg_data.seq % 1000 == 0:
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=msg_data.seq)
            )
            logger.debug("Updated repos cursor for %s to %s", service_did, msg_data.seq)

            SubscriptionState.update(cursor=msg_data.seq).where(
                SubscriptionState.service == service_did
            ).where(SubscriptionState.firehose_type == FirehoseType.REPOS).execute()

        # Skip commits with empty blocks, any commit containing data for the necessary
        # record types will always have CAR blocks
        if not msg_data.blocks:
            return

        ops = _get_commit_ops_by_type(msg_data)
        try:
            callback(ops)
        except Exception:  # noqa: PIE786
            logger.exception(
                "%s\nCursor: %s%s",
                style("Error in commit operations callback", fg="red", bold=True),
                msg_data.seq,
                _get_commit_details_str(msg_data),
            )

        msg_data = frame = None

    def on_error_handler(error: BaseException):
        _log_message_error(frame, msg_data)

    client.start(on_message_handler, on_error_handler)


def _run_labels_client(
    service_did: str,
    callback: _LabelsMessageCallbackType,
    stream_stop_event: Optional[Event] = None,
    relay_server: str = "mod.bsky.app",  # unused
):
    state = SubscriptionState.get_or_none(
        (SubscriptionState.service == service_did)
        & (SubscriptionState.firehose_type == FirehoseType.LABELS)
    )
    params = None
    if state:
        params = models.ComAtprotoLabelSubscribeLabels.Params(cursor=state.cursor)

    client = FirehoseSubscribeLabelsClient(params)

    if not state:
        state = SubscriptionState.create(
            service=service_did, cursor=0, firehose_type=FirehoseType.LABELS
        )

    frame: firehose_models.Frame | None = None
    msg_data: SubscribeLabelsMessage | None = None
    queued_cursor: int = state.cursor

    def on_message_handler(message: firehose_models.MessageFrame):
        # Stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        nonlocal frame, msg_data
        frame = message
        msg_data = parse_subscribe_labels_message(message)
        if not isinstance(msg_data, models.ComAtprotoLabelSubscribeLabels.Labels):
            return

        nonlocal queued_cursor
        prev_cursor = queued_cursor
        try:
            queued_cursor = callback(msg_data) // 10 * 10
        except Exception:  # noqa: PIE786
            logger.exception(
                "%s\nData: %s",
                style("Error in labels message callback", fg="red", bold=True),
                msg_data,
            )

        # Update cursor every ~10 messages in case we get disconnected
        current_cursor = msg_data.seq
        if current_cursor % 10 == 0:
            client.update_params(
                models.ComAtprotoLabelSubscribeLabels.Params(cursor=current_cursor)
            )
            logger.debug(
                "Updated labels cursor for %s to %s", service_did, current_cursor
            )

        # Save cursor before/at first label message in queue (in case there are labels
        # left in queue at shutdown) or every ~10 messages
        if prev_cursor < queued_cursor:
            SubscriptionState.update(cursor=queued_cursor).where(
                SubscriptionState.service == service_did
            ).where(SubscriptionState.firehose_type == FirehoseType.LABELS).execute()
            logger.debug(
                "Saved labels cursor for %s to database: %s", service_did, queued_cursor
            )

        msg_data = frame = None

    def on_error_handler(error: BaseException):
        _log_message_error(frame, msg_data)

    client.start(on_message_handler, on_error_handler)


def run(
    service_did: str,
    callback: _ReposOperationsCallbackType | _LabelsMessageCallbackType,
    stream_stop_event=None,
    labels=False,
    relay_server: str | None = None,
):
    """
    Start a firehose data stream client.

    :param labels: If True, subscribe to the labels firehose instead. Defaults to False
    :param relay_server: (Optional) hostname of the firehose relay server to connect.
        By default, the client will connect to `bsky.network` (repos) or `mod.bsky.app`
        (labels).
    """
    client_func = _run_repos_client
    if labels:
        client_func = _run_labels_client

    logger.info(
        style("Starting %s firehose data stream...", fg="yellow"),
        "labels" if labels else "repos",
    )
    while stream_stop_event is None or not stream_stop_event.is_set():
        try:
            params = {
                "service_did": service_did,
                "callback": callback,
                "stream_stop_event": stream_stop_event,
            }
            if relay_server:
                params["relay_server"] = relay_server

            client_func(**params)
        except FirehoseError:
            # Log error details and reconnect to firehose
            reconnect = stream_stop_event and not stream_stop_event.is_set()
            log_header = "Error encountered in data stream"
            if reconnect:
                log_header = f"{log_header}, reconnecting..."

            logger.exception(style(log_header, fg="red", bold=True))
            if reconnect:
                sleep(3)

    logger.info(
        style("%s firehose data stream stopped", fg="yellow"),
        "Labels" if labels else "Repos",
    )
