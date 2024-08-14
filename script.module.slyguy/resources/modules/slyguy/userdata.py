from copy import deepcopy
from slyguy import settings, signals


data = None

# lazy load data
def _get_data():
    global data
    if data is None:
        data = deepcopy(settings.USERDATA.value)
    return data


def get(key, default=None):
    return _get_data().get(key, default)


def set(key, value):
    _get_data()[key] = value


def pop(key, default=None):
    return _get_data().pop(key, default)


def delete(key):
    if key in _get_data():
        del data[key]

def clear():
    data.clear()


@signals.on(signals.ON_CLOSE)
def save_data():
    if data is not None:
        settings.USERDATA.value = data
