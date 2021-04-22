import json

from kodi_six import xbmcaddon

from .constants import ADDON, COMMON_ADDON
from . import signals

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    #refresh settings
    global ADDON
    ADDON = xbmcaddon.Addon(ADDON.getAddonInfo('id'))
    common_settings.reset()

def open():
    ADDON.openSettings()

def getDict(key, default=None):
    try:
        return json.loads(get(key))
    except:
        return default

def setDict(key, value):
    set(key, json.dumps(value, separators=(',', ':')))

def getInt(key, default=None):
    try:
        return int(get(key))
    except:
        return default

def getFloat(key, default=None):
    try:
        return float(get(key))
    except:
        return default

def setInt(key, value):
    set(key, int(value))

def getBool(key, default=False):
    value = get(key).lower()
    if not value:
        return default
    else:
        return value == 'true'

def getEnum(key, choices=None, default=None):
    index = getInt(key)
    if index == None or not choices:
        return default

    try:
        return choices[index]
    except KeyError:
        return default

def remove(key):
    set(key, '')

def setBool(key, value=True):
    set(key, 'true' if value else 'false')

def get(key, default=''):
    return ADDON.getSetting(key) or default

def set(key, value=''):
    ADDON.setSetting(key, str(value))

def is_fresh():
    fresh = getBool('_fresh', True)

    if fresh:
        setBool('_fresh', False)

    return fresh

class Settings(object):
    _fresh = False

    @property
    def fresh(self):
        return self._fresh

    def __init__(self, _addon=None):
        self._addon = _addon or ADDON

    def is_fresh(self):
        fresh = self.getBool('_fresh', True)
        
        if fresh:
            self.setBool('_fresh', False)

        return fresh

    def open(self):
        self._addon.openSettings()

    def getDict(self, key, default=None):
        try:
            return json.loads(self.get(key))
        except:
            return default

    def reset(self):
        self._addon = xbmcaddon.Addon(self._addon.getAddonInfo('id'))

    def setDict(self, key, value):
        self.set(key, json.dumps(value, separators=(',', ':')))

    def getInt(self, key, default=None):
        try:
            return int(self.get(key))
        except:
            return default

    def getFloat(self, key, default=None):
        try:
            return float(self.get(key))
        except:
            return default

    def setInt(self, key, value):
        self.set(key, int(value))

    def getBool(self, key, default=False):
        value = self.get(key).lower()
        if not value:
            return default
        else:
            return value == 'true'

    def getEnum(self, key, choices=None, default=None):
        index = self.getInt(key)
        if index == None or not choices:
            return default

        try:
            return choices[index]
        except KeyError:
            return default

    def remove(self, key):
        self.set(key, '')

    def setBool(self, key, value=True):
        self.set(key, 'true' if value else 'false')

    def get(self, key, default=''):
        return self._addon.getSetting(key) or default

    def set(self, key, value=''):
        self._addon.setSetting(key, str(value))

common_settings = Settings(COMMON_ADDON)