import csv
from pathlib import Path, PurePath

from click import style

from server.logger import logger


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
