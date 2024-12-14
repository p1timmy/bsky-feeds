from collections import defaultdict

from atproto import (
    CAR,
    AtUri,
    FirehoseSubscribeReposClient,
    firehose_models,
    models,
    parse_subscribe_repos_message,
)
from atproto.exceptions import FirehoseError
from click import style

from server.database import SubscriptionState
from server.logger import logger

_INTERESTED_RECORDS = {
    models.AppBskyFeedPost: models.ids.AppBskyFeedPost,
}


def _get_ops_by_type(commit: models.ComAtprotoSyncSubscribeRepos.Commit) -> defaultdict:
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

            create_info = {"uri": str(uri), "cid": str(op.cid), "author": commit.repo}

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
                        {"record": record, **create_info}
                    )
                    break

        if op.action == "delete":
            operation_by_type[uri.collection]["deleted"].append({"uri": str(uri)})

    return operation_by_type


def run(name, operations_callback, stream_stop_event=None):
    logger.info(style("Starting data stream...", fg="yellow"))

    while stream_stop_event is None or not stream_stop_event.is_set():
        try:
            _run(name, operations_callback, stream_stop_event)
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

    logger.info(style("Data stream stopped", fg="yellow"))


def _run(name, operations_callback, stream_stop_event=None):
    state = SubscriptionState.get_or_none(SubscriptionState.service == name)

    params = None
    if state:
        params = models.ComAtprotoSyncSubscribeRepos.Params(cursor=state.cursor)

    client = FirehoseSubscribeReposClient(params)

    if not state:
        SubscriptionState.create(service=name, cursor=0)

    def on_message_handler(message: firehose_models.MessageFrame) -> None:
        # stop on next message if requested
        if stream_stop_event and stream_stop_event.is_set():
            client.stop()
            return

        # BUG: Random model validation errors caused by broken/blank messages
        # (https://github.com/MarshalX/atproto/issues/186)
        commit = parse_subscribe_repos_message(message)
        if not isinstance(commit, models.ComAtprotoSyncSubscribeRepos.Commit):
            return

        # Update stored state every ~1000 events (up from 20 due to recent increase in
        # network activity)
        if commit.seq % 1000 == 0:
            logger.debug("Updated cursor for %s to %s", name, commit.seq)
            client.update_params(
                models.ComAtprotoSyncSubscribeRepos.Params(cursor=commit.seq)
            )
            SubscriptionState.update(cursor=commit.seq).where(
                SubscriptionState.service == name
            ).execute()

        if not commit.blocks:
            return

        operations_callback(_get_ops_by_type(commit))

    client.start(on_message_handler)
