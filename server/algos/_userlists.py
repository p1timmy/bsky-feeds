import csv
from collections.abc import Collection
from pathlib import Path, PurePath
from typing import NamedTuple, Optional

from click import style

from server.api_client import get_client, get_list_members
from server.logger import logger


class UserList(NamedTuple):
    """
    Container for a user list (a `set` of user DIDs) and its metadata

    :param csv_filename: Name of CSV file in the `lists` directory to load list members
    :param member_dids: A `set` of `str`s containing list member DIDs
    :param description: The description of the user list as shown in logs
    :param uri: ATProto URI to a live version of the user list on Bluesky.
        Setting this to an empty string or None prevents the user list from being updated.

        Defaults to None.
    """

    csv_filename: str
    member_dids: set[str]
    description: str
    uri: Optional[str] = None


def load_user_list(filename: str, user_set: set[str]):
    """
    Load a list of user DIDs from a CSV file in the `lists` directory

    :param filename: Name of the CSV file to load
    :param user_set: `set` instance where DIDs will be added into

    :raises KeyError: If the CSV file is missing a `did` column
    """
    module_dir = PurePath(__file__).parent
    user_list_path = Path(*module_dir.parts[:-2], "lists", filename)
    with user_list_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_did = row["did"]

            # TODO: check if it's a valid DID
            if user_did.startswith("did:"):
                user_set.add(user_did)


def load_user_list_with_logs(filename: str, user_set: set[str], list_desc: str):
    """
    Same as `load_user_list` but with log entries added for use while running the feed
    generator server

    :param filename: Name of the CSV file to load
    :param user_set: `set` instance where DIDs will be added into
    :param list_desc: Description of the list being loaded, to be shown in logs
    """
    initial_count = len(user_set)
    try:
        load_user_list(filename, user_set)
    except Exception:  # noqa: PIE786
        logger.warning(
            style("Failed to load %s", fg="yellow", bold=True), list_desc, exc_info=True
        )
    else:
        added_count = len(user_set) - initial_count
        if added_count > 0:
            logger.info("Loaded DIDs in %s: %d", list_desc, added_count)


def update_user_lists(userlists: Collection[UserList]):
    # Create new client instance here to log in/check session once before retrieving
    # the first list
    client = get_client()

    for user_list_info in userlists:
        if not user_list_info.uri:
            continue

        member_dids = set(
            {member.did for member in get_list_members(user_list_info.uri, client)}
        )

        user_did_set = user_list_info.member_dids
        initial_count = len(user_did_set)
        dids_to_add = member_dids.difference(user_did_set)
        dids_to_remove = user_did_set.difference(member_dids)

        user_did_set.update(dids_to_add)
        user_did_set.difference_update(dids_to_remove)

        # TODO: Save to file to preserve updates between restarts without having to wait
        # for Git repo to be updated

        if (len(user_did_set) - initial_count) != 0:
            logger.info(
                style("Updated %s: added %d, removed %d", fg="green"),
                user_list_info.description,
                len(dids_to_add),
                len(dids_to_remove),
            )
