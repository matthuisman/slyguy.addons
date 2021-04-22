from . import settings
from .constants import ADDON, USERDATA_KEY

def _get_data():
    return settings.getDict(USERDATA_KEY, {})

def get(key, default=None):
    return _get_data().get(key, default)

def set(key, value):
    data = _get_data()
    data[key] = value
    _set_data(data)

def _set_data(data):
    settings.setDict(USERDATA_KEY, data)

def pop(key, default=None):
    data = _get_data()
    value = data.pop(key, default)
    _set_data(data)
    return value

def delete(key):
    data = _get_data()
    if key in data:
        del data[key]
        _set_data(data)
    
def clear():
    _set_data({})

class Userdata(object):
    def __init__(self, _addon=None):
        self._settings = settings.Settings(_addon or ADDON)

    def _get_data(self):
        return self._settings.getDict(USERDATA_KEY, {})

    def get(self, key, default=None):
        return self._get_data().get(key, default)

    def set(self, key, value):
        data = self._get_data()
        data[key] = value
        self._set_data(data)

    def _set_data(self, data):
        self._settings.setDict(USERDATA_KEY, data)

    def pop(self, key, default=None):
        data = self._get_data()
        value = data.pop(key, default)
        self._set_data(data)
        return value

    def delete(self, key):
        data = self._get_data()
        if key in data:
            del data[key]
            self._set_data(data)
        
    def clear(self):
        self._set_data({})