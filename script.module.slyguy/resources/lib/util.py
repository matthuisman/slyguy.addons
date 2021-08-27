from time import time
from distutils.version import LooseVersion

from kodi_six import xbmc

from slyguy import settings
from slyguy.log import log
from slyguy.session import Session
from slyguy.util import kodi_rpc, get_addon

from .constants import *

def get_slyguy_addons():
    return Session(timeout=15).gz_json(ADDONS_URL)

def check_updates(force=False):
    _time = int(time())
    if not force and _time < settings.getInt('_last_updates_check', 0) + UPDATES_CHECK_TIME:
        return

    settings.setInt('_last_updates_check', _time)

    new_md5 = Session(timeout=15).get(ADDONS_MD5).text.split(' ')[0]
    if not force and new_md5 == settings.get('addon_md5'):
        return 0

    settings.set('_addon_md5', new_md5)

    updates = []
    slyguy_addons = get_slyguy_addons()
    slyguy_installed = [x['addonid'] for x in kodi_rpc('Addons.GetAddons', {'installed': True, 'enabled': True})['addons'] if x['addonid'] in slyguy_addons]

    for addon_id in slyguy_installed:
        addon = get_addon(addon_id, install=False)
        if not addon:
            continue

        cur_version = addon.getAddonInfo('version')
        new_version = slyguy_addons[addon_id]['version']

        if LooseVersion(cur_version) < LooseVersion(new_version):
            updates.append([addon, cur_version, new_version])

    if not force and not updates:
        return 0

    log.debug('Updating repos due to {} addon updates'.format(len(updates)))
    xbmc.executebuiltin('UpdateAddonRepos')
    return updates
