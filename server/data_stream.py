from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import Event
from typing import Optional

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
from click import style

from server.database import FirehoseType, SubscriptionState
from server.logger import logger

_INTERESTED_RECORDS = {
    models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
}
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


def _run_repos_client(
    service_did: str, operations_callback, stream_stop_event: Optional[Event] = None
):
    state = SubscriptionState.get_or_none(
        (SubscriptionState.service == service_did)
        & (SubscriptionState.firehose_type == FirehoseType.REPOS)
    )
    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)

    client = FirehoseSubscribeReposClient(params)

    if not state:
        SubscriptionState.create(
            service=service_did, cursor=0, firehose_type=FirehoseType.REPOS
        )

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        # stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        # BUG: Random model validation errors caused by broken/blank messages
        # (https://github.com/MarshalX/atproto/issues/186)
        commit = parse_subscribe_repos_message(message)

        global repos_last_message_time
        message_ts = datetime.fromisoformat(commit.time)
        if message_ts > repos_last_message_time:
            repos_last_message_time = message_ts

        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            return

        # Update stored state every ~1000 events (up from 20 due to recent increase in
        # network activity)
        if commit.seq % 1000 == 0:
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq)
            )
            logger.debug("Updated repos cursor for %s to %s", service_did, commit.seq)

            SubscriptionState.update(cursor=commit.seq).where(
                SubscriptionState.service == service_did
            ).where(SubscriptionState.firehose_type == FirehoseType.REPOS).execute()

        if not commit.blocks:
            return

        operations_callback(_get_commit_ops_by_type(commit))

    client.start(on_message_handler)


def _run_labels_client(
    service_did: str,
    labels_message_callback: Callable[
        [models.ComAtprotoLabelSubscribeLabels.Labels], int
    ],
    stream_stop_event: Optional[Event] = None,
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

    queued_cursor: int = state.cursor

    def on_message_handler(message: firehose_models.MessageFrame):
        # Stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        labels_message = parse_subscribe_labels_message(message)
        if not isinstance(labels_message, models.ComAtprotoLabelSubscribeLabels.Labels):
            return

        nonlocal queued_cursor
        prev_cursor = queued_cursor
        queued_cursor = labels_message_callback(labels_message) // 10 * 10

        # Update cursor every ~10 messages in case we get disconnected
        current_cursor = labels_message.seq
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

    client.start(on_message_handler)


def run(service_did: str, on_message_callback, stream_stop_event=None, labels=False):
    """
    Start a firehose data stream client.

    :param labels: If True, subscribe to the labels firehose instead. Defaults to False
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
            client_func(service_did, on_message_callback, stream_stop_event)
        except FirehoseError:
            # Log error details and reconnect to firehose
            log_header = "Error encountered in data stream"
            if stream_stop_event and not stream_stop_event.is_set():
                log_header = f"{log_header}, reconnecting..."

            logger.error(style(log_header, fg="red", bold=True), exc_info=True)

    logger.info(
        style("%s firehose data stream stopped", fg="yellow"),
        "Labels" if labels else "Repos",
    )
