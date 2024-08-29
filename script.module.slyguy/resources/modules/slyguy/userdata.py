from slyguy import settings
from slyguy.settings.types import USERDATA_KEY_FMT


def get(key, default=None):
    return settings.get(USERDATA_KEY_FMT.format(key=key), default)


def set(key, value):
    settings.set(USERDATA_KEY_FMT.format(key=key), value)


def pop(key, default=None):
    return settings.pop(USERDATA_KEY_FMT.format(key=key), default)


def delete(key):
    settings.delete(USERDATA_KEY_FMT.format(key=key))
