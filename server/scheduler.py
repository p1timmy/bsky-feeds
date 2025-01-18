from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from server.algos import userlists
from server.algos._userlists import update_user_lists


def setup_scheduler() -> BackgroundScheduler:
    """
    Create a `BackgroundScheduler` instance with jobs added to it
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        update_user_lists, trigger=IntervalTrigger(minutes=20), args=[userlists]
    )
    return scheduler
