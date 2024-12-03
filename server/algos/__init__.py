from . import _base, lovelive

algos = {
    lovelive.uri: _base.handler,
}

filters = {
    lovelive.uri: lovelive.filter,
}
