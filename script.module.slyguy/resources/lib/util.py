import os
from time import time
from looseversion import LooseVersion

from kodi_six import xbmc

from slyguy import settings, log, _
from slyguy.session import Session
from slyguy.util import kodi_rpc, get_addon, safe_copy
from slyguy.constants import UPDATE_TIME_LIMIT, REPO_ADDON_ID, REPO_DOMAIN

from .constants import *


def get_slyguy_addons():
    with Session(timeout=15) as session:
        return session.gz_json(ADDONS_URL)


def check_updates(force=False):
    _time = int(time())
    if not force and _time < settings.getInt('_last_updates_check', 0) + UPDATES_CHECK_TIME:
        return

    settings.setInt('_last_updates_check', _time)
    with Session(timeout=15) as session:
        new_md5 = session.get(ADDONS_MD5).text.split(' ')[0]

    if not force and new_md5 == settings.get('addon_md5'):
        return 0
    settings.set('_addon_md5', new_md5)

    pending_updates = {}
    slyguy_addons = get_slyguy_addons()
    slyguy_installed = [x['addonid'] for x in kodi_rpc('Addons.GetAddons', {'installed': True, 'enabled': True})['addons'] if x['addonid'] in slyguy_addons]

    update_times = settings.getDict('_updates', {})
    new_update_times = {}
    for addon_id in slyguy_installed:
        addon = get_addon(addon_id, install=False)
        if not addon:
            continue

        name = addon.getAddonInfo('name')
        cur_version = addon.getAddonInfo('version')
        new_version = slyguy_addons[addon_id]['version']

        if (LooseVersion(new_version).version[0] - LooseVersion(cur_version).version[0]) > 5.0:
            # if major version more than 5 ahead. ignore
            log.debug('{}: New version {} major more than 5 versions ahead of current version {}. Ignoring update'.format(
                addon_id, new_version, cur_version
            ))
            continue

        if LooseVersion(cur_version) < LooseVersion(new_version):
            pending_updates[addon_id] = {'name': name, 'cur': cur_version, 'new': new_version}

            new_update_times[addon_id] = [cur_version, _time]
            if addon_id in update_times and update_times[addon_id][0] == cur_version:
                new_update_times[addon_id][1] = update_times[addon_id][1]

    settings.setDict('_updates', new_update_times)
    if not force and not pending_updates:
        return 0

    log.debug('Updating repos due to {} addon updates'.format(len(pending_updates)))
    xbmc.executebuiltin('UpdateAddonRepos')
    return pending_updates

def check_repo():
    addon = get_addon(REPO_ADDON_ID, install=True, required=True)
    update_time = settings.getDict('_updates', {}).get(REPO_ADDON_ID)
    if not update_time or addon.getAddonInfo('version') != update_time[0] or time() < update_time[1] + UPDATE_TIME_LIMIT:
        return

    log.info('Repo: {} requires force update'.format(REPO_ADDON_ID))

    addon_path = xbmc.translatePath(addon.getAddonInfo('path'))

    with Session(timeout=15) as session:
        session.chunked_dl('{0}/.repo/{1}/{1}/addon.xml'.format(REPO_DOMAIN, REPO_ADDON_ID), os.path.join(addon_path, 'addon.xml.downloading'))
        safe_copy(os.path.join(addon_path, 'addon.xml.downloading'), os.path.join(addon_path, 'addon.xml'), del_src=True)
        session.chunked_dl('{0}/.repo/{1}/{1}/icon.png'.format(REPO_DOMAIN, REPO_ADDON_ID), os.path.join(addon_path, 'icon.png.downloading'))
        safe_copy(os.path.join(addon_path, 'icon.png.downloading'), os.path.join(addon_path, 'icon.png'), del_src=True)

    xbmc.executebuiltin('UpdateLocalAddons')
