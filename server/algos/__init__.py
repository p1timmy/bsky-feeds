from . import _base, lovelive
from ._base import MalformedCursorError  # noqa: F401

algos = {
    lovelive.uri: _base.handler,
}

filters = {
    lovelive.uri: lovelive.filter,
}
