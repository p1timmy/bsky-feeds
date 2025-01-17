from . import _base, lovelive
from ._base import MalformedCursorError  # noqa: F401
from ._userlists import UserList, load_user_list_with_logs

algos = {
    lovelive.uri: _base.handler,
}

filters = {
    lovelive.uri: lovelive.filter,
}

userlists = [
    UserList(
        "lovelive_users.csv",
        lovelive.DEDICATED_USERS,
        "dedicated LoveLive accounts list",
    ),
    UserList(
        "lovelive_ignore_users.csv",
        lovelive.IGNORE_USERS,
        "LoveLive!Sky feed user ignore list",
    ),
]

for userlist in userlists:
    load_user_list_with_logs(*userlist)
