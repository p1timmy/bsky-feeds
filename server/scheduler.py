from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from server.algos import userlists
from server.algos._userlists import update_user_lists


def setup_scheduler(user_list_updates: bool = True) -> Optional[BackgroundScheduler]:
    """
    Create a `BackgroundScheduler` instance with jobs added to it

    :param user_list_updates: Whether to add a scheduled job for updating user lists
        in the background. Default is True
    :return: `None` if username and/or password for the Bluesky API in config are
        invalid or missing/unset, otherwise a new `BackgroundScheduler` instance
    """
    if user_list_updates:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            update_user_lists, trigger=IntervalTrigger(minutes=20), args=[userlists]
        )
        return scheduler
