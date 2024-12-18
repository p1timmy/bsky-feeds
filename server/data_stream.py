from collections import defaultdict
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

            # Drop events not supported by ATproto SDK to prevent log spamming
            if record is None:
                continue

            for record_type, record_nsid in _INTERESTED_RECORDS.items():
                if uri.collection == record_nsid and models.is_record_type(
                    record, record_type
                ):
                    operation_by_type[record_nsid]["created"].append(
                        {
                            "record": record,
                            "uri": str(uri),
                            "cid": str(op.cid),
                            "author": commit.repo,
                        }
                    )
                    break

        if op.action == "delete":
            operation_by_type[uri.collection]["deleted"].append({"uri": str(uri)})

    return operation_by_type


def _run_repos_client(
    name: str, operations_callback, stream_stop_event: Optional[Event] = None
):
    state = SubscriptionState.get_or_none(
        (SubscriptionState.service == name)
        & (SubscriptionState.firehose_type == FirehoseType.REPOS)
    )
    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)

    client = FirehoseSubscribeReposClient(params)

    if not state:
        SubscriptionState.create(
            service=name, cursor=0, firehose_type=FirehoseType.REPOS
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
            logger.debug("Updated repos cursor for %s to %s", name, commit.seq)

            SubscriptionState.update(cursor=commit.seq).where(
                SubscriptionState.service == name
            ).where(SubscriptionState.firehose_type == FirehoseType.REPOS).execute()

        if not commit.blocks:
            return

        operations_callback(_get_commit_ops_by_type(commit))

    client.start(on_message_handler)


def _run_labels_client(
    name: str, labels_message_callback, stream_stop_event: Optional[Event] = None
):
    state = SubscriptionState.get_or_none(
        (SubscriptionState.service == name)
        & (SubscriptionState.firehose_type == FirehoseType.LABELS)
    )

    params = None
    if state:
        params = models.ComAtprotoLabelSubscribeLabels.Params(cursor=state.cursor)

    client = FirehoseSubscribeLabelsClient(params)

    if not state:
        SubscriptionState.create(
            service=name, cursor=0, firehose_type=FirehoseType.LABELS
        )

    def on_message_handler(message: firehose_models.MessageFrame):
        # Stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        labels_message = parse_subscribe_labels_message(message)
        if not isinstance(labels_message, models.ComAtprotoLabelSubscribeLabels.Labels):
            return

        # Update cursor every ~10 messages in case we get disconnected
        if labels_message.seq % 10 == 0:
            client.update_params(
                models.ComAtprotoLabelSubscribeLabels.Params(cursor=labels_message.seq)
            )
            logger.debug("Updated labels cursor for %s to %s", name, labels_message.seq)

            SubscriptionState.update(cursor=labels_message.seq).where(
                SubscriptionState.service == name
            ).where(SubscriptionState.firehose_type == FirehoseType.LABELS).execute()

        labels_message_callback(labels_message)

    client.start(on_message_handler)


def run(name: str, on_message_callback, stream_stop_event=None, labels=False):
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
            client_func(name, on_message_callback, stream_stop_event)
        except FirehoseError:
            # Log error details and reconnect to firehose
            logger.error(
                style(
                    "Error encountered in data stream, reconnecting...",
                    fg="red",
                    bold=True,
                ),
                exc_info=True,
            )

    logger.info(
        style("%s firehose data stream stopped", fg="yellow"),
        "Labels" if labels else "Repos",
    )
