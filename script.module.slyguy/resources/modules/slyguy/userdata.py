from copy import deepcopy
from slyguy import settings
from slyguy.constants import USERDATA_KEY


#TODO: Redo to cache
# then write just on persist
def _get_data():
    return deepcopy(settings.getDict(USERDATA_KEY, {}))

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
