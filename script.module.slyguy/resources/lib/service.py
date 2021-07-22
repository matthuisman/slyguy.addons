import os
import json
from time import time
from threading import Thread
from distutils.version import LooseVersion

from kodi_six import xbmc

from slyguy import gui, router, settings
from slyguy.session import Session
from slyguy.util import kodi_rpc, get_addon
from slyguy.log import log
from slyguy.constants import ROUTE_SERVICE, ROUTE_SERVICE_INTERVAL, KODI_VERSION

from .proxy import Proxy
from .monitor import monitor
from .player import Player
from .constants import *

session = Session(timeout=15)

def _check_updates():
    _time = int(time())
    if _time < settings.getInt('_last_updates_check', 0) + UPDATES_CHECK_TIME:
        return

    settings.setInt('_last_updates_check', _time)

    new_md5 = session.get(ADDONS_MD5).text.split(' ')[0]
    if new_md5 == settings.get('addon_md5'):
        return

    settings.set('_addon_md5', new_md5)

    updates = []
    slyguy_addons = session.gz_json(ADDONS_URL)
    slyguy_installed = [x['addonid'] for x in kodi_rpc('Addons.GetAddons', {'installed': True, 'enabled': True})['addons'] if x['addonid'] in slyguy_addons]

    for addon_id in slyguy_installed:
        addon = get_addon(addon_id, install=False)
        if not addon:
            continue

        cur_version = addon.getAddonInfo('version')
        new_version = slyguy_addons[addon_id]['version']

        if LooseVersion(cur_version) < LooseVersion(new_version):
            updates.append([addon_id, cur_version, new_version])

    if not updates:
        return

    log.debug('Updating repos due to {} addon updates'.format(len(updates)))
    xbmc.executebuiltin('UpdateAddonRepos')

def _check_news():
    _time = int(time())
    if _time < settings.getInt('_last_news_check', 0) + NEWS_CHECK_TIME:
        return

    settings.setInt('_last_news_check', _time)

    news = session.gz_json(NEWS_URL)
    if not news:
        return

    if 'id' not in news or news['id'] == settings.get('_last_news_id'):
        return

    settings.set('_last_news_id', news['id'])
    settings.set('_news', json.dumps(news))

def start():
    log.debug('Shared Service: Started')

    player = Player()
    proxy = Proxy()

    try:
        proxy.start()
    except Exception as e:
        log.error('Failed to start proxy server')
        log.exception(e)

    ## Inital wait on boot
    monitor.waitForAbort(5)

    try:
        while not monitor.abortRequested():
            try: _check_news()
            except Exception as e: log.exception(e)

            try: _check_updates()
            except Exception as e: log.exception(e)

            if monitor.waitForAbort(60):
                break
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.exception(e)

    try: proxy.stop()
    except: pass

    log.debug('Shared Service: Stopped')
