import json
import os

from kodi_six import xbmc, xbmcaddon

from slyguy.constants import ADDON, ADDON_ID
from slyguy import signals
from slyguy.log import log
from slyguy.util import remove_file


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    reset()
    check_corrupt(ADDON)

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
    if addon is None:
        # stop in-memory values getting written
        reset()
        addon = ADDON
    addon.setSetting(key, str(value))


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
