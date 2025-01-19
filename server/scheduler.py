from typing import Optional

import validators
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from server import config
from server.algos import userlists
from server.algos._userlists import update_user_lists


def setup_scheduler() -> Optional[BackgroundScheduler]:
    """
    Create a `BackgroundScheduler` instance with jobs added to it

    :return: `None` if username and/or password for the Bluesky API in config are
    invalid or missing/unset, otherwise a new `BackgroundScheduler` instance
    """

    if all([config.HANDLE, config.PASSWORD, validators.domain(config.HANDLE) is True]):
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            update_user_lists, trigger=IntervalTrigger(minutes=20), args=[userlists]
        )
        return scheduler
