from . import _base, lovelive
from ._base import MalformedCursorError  # noqa: F401
from ._userlists import UserList, load_user_list_with_logs

algos = {
    lovelive.uri: _base.handler,
}

algo_names = {
    lovelive.uri: lovelive.__name__.split(".")[-1],
}

filters = {
    lovelive.uri: lovelive.filter,
}

userlists = [
    UserList(
        "lovelive_users.csv",
        lovelive.DEDICATED_USERS,
        "dedicated LoveLive accounts list",
        uri=lovelive.dedicated_userlist_uri,
    ),
    UserList(
        "lovelive_users_media_only.csv",
        lovelive.DEDICATED_USERS_MEDIA_ONLY,
        "dedicated LoveLive accounts list (media posts only)",
        uri=lovelive.dedicated_userlist_media_only_uri,
    ),
    UserList(
        "lovelive_ignore_users.csv",
        lovelive.IGNORE_USERS,
        "LoveLive!Sky feed user ignore list",
        uri=lovelive.ignore_list_uri,
    ),
]

for _userlist in userlists:
    load_user_list_with_logs(
        _userlist.csv_filename, _userlist.member_dids, _userlist.description
    )
