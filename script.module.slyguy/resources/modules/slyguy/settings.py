import json
import os

from kodi_six import xbmc, xbmcaddon

from .constants import ADDON, ADDON_ID, COMMON_ADDON
from . import signals
from .log import log
from .util import remove_file

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    reset()
    check_corrupt(ADDON)
    common_settings.reset()

def reset():
    global ADDON
    ADDON = xbmcaddon.Addon(ADDON.getAddonInfo('id'))

def open():
    ADDON.openSettings()

def getDict(key, default=None):
    try:
        return json.loads(get(key))
    except:
        return default

def getJSON(key, default=None):
    return getDict(key, default)

def setDict(key, value):
    set(key, json.dumps(value, separators=(',', ':')))

def setJSON(key, value):
    setDict(key, value)

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

def set(key, value='', addon=None):
    signals.skip_next(signals.ON_SETTINGS_CHANGE)
    addon = addon or ADDON
    addon.setSetting(key, str(value))

class Settings(object):
    def __init__(self, _addon=None):
        self._addon = _addon or ADDON
        check_corrupt(self._addon)

    def open(self):
        self._addon.openSettings()

    def getDict(self, key, default=None):
        try:
            return json.loads(self.get(key))
        except:
            return default

    def getJSON(self, key, default=None):
        return self.getDict(key, default)

    def reset(self):
        self._addon = xbmcaddon.Addon(self._addon.getAddonInfo('id'))

    def setDict(self, key, value):
        self.set(key, json.dumps(value, separators=(',', ':')))

    def setJSON(self, key, value):
        self.setDict(key, value)

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
        set(key, value, addon=self._addon)

def check_corrupt(addon):
    if addon.getAddonInfo('id') != ADDON_ID:
        return

    fresh = addon.getSetting('_fresh')
    if fresh == 'false':
        return

    set('_fresh', 'false', addon=addon)
    addon = xbmcaddon.Addon(addon.getAddonInfo('id'))

    if addon.getSetting('_fresh') != 'false':
        file_path = os.path.join(xbmc.translatePath(addon.getAddonInfo('profile')), 'settings.xml')
        log.debug('Removing corrupt settings.xml: {}'.format(file_path))
        remove_file(file_path)
        addon = xbmcaddon.Addon(addon.getAddonInfo('id'))
        set('_fresh', 'false', addon=addon)

common_settings = Settings(COMMON_ADDON)
