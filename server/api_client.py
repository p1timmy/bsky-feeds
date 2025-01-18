import logging
from pathlib import Path, PurePath
from typing import Optional

from atproto import Client
from atproto_client import Session, SessionEvent, models

from server.config import HANDLE, PASSWORD

SESSION_PATH = Path(PurePath(__file__).parents[1], f"session_{HANDLE}.txt")
logger = logging.getLogger(__name__)


def _get_session() -> Optional[str]:
    try:
        with SESSION_PATH.open() as f:
            return f.read()
    except OSError:
        return None


def _save_session(session_string: str):
    with SESSION_PATH.open("w") as f:
        f.write(session_string)


def _on_session_change(event: SessionEvent, session: Session):
    logger.debug("Session changed: %s %s", event, repr(session))
    if event in (SessionEvent.CREATE, SessionEvent.REFRESH):
        logger.debug("Saving changed session")
        _save_session(session.export())


def get_client() -> Client:
    """
    Get a new Bluesky API client instance that's ready to use
    """

    client = Client()
    client.on_session_change(_on_session_change)

    session_string = _get_session()
    if session_string and HANDLE in session_string:
        logger.debug("Reusing existing session")
        client.login(session_string=session_string)
    else:
        logger.debug("Creating new client session")
        client.login(HANDLE, PASSWORD)

    return client


def get_list_members(
    list_uri: str, client: Optional[Client] = None
) -> list[models.AppBskyActorDefs.ProfileView]:
    """
    Get a list of accounts in a Bluesky list

    :param list_uri: The ATProto URI of the list
    :param client: (Optional) A `Client` instance to use for making requests
    :return: A `list` of `ProfileView`s containing details of each member's account
    """
    cursor: Optional[str] = None
    members: list[models.AppBskyActorDefs.ProfileView] = []

    if client is None:
        client = get_client()

    while True:
        params = models.AppBskyGraphGetList.Params(
            list=list_uri, limit=100, cursor=cursor
        )
        response: models.AppBskyGraphGetList.Response = client.app.bsky.graph.get_list(
            params
        )
        members += [item.subject for item in response.items]

        if response.cursor is None:
            break

        cursor = response.cursor

    return members
