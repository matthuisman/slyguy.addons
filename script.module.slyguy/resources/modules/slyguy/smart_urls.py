import os

import requests
from kodi_six import xbmc, xbmcaddon

from slyguy import settings, is_donor, log
from slyguy.log import log
from slyguy.mem_cache import cached
from slyguy.constants import ADDON_ID, COMMON_ADDON_ID


def get_dns_rewrites(dns_rewrites=None, addon_id=ADDON_ID):
    if is_donor():
        rewrites = _load_rewrites(addon_id)
        if COMMON_ADDON_ID != addon_id:
            rewrites.extend(_load_rewrites(COMMON_ADDON_ID))
    else:
        rewrites = []

    if dns_rewrites:
        rewrites.extend(dns_rewrites)

    if settings.get('dns_server'):
        rewrites.append(['r:{}'.format(settings.get('dns_server')), '*'])

    return rewrites


@cached(expires=60*5)
def _get_url(url):
    log.debug('Request DNS URL: {}'.format(url))
    return requests.get(url).text


def _load_rewrites(addon_id):
    rewrites = []

    file_names = [
        'urls.txt',
        'dns_rewrites.txt', #legacy
    ]

    try:
        directory = xbmc.translatePath(xbmcaddon.Addon(addon_id).getAddonInfo('profile'))
    except:
        return rewrites

    found = False
    for name in file_names:
        file_path = os.path.join(xbmc.translatePath(directory), name)
        if os.path.exists(file_path):
            found = True
            break

    if not found:
        return rewrites

    try:
        def _process_lines(lines):
            for line in lines:
                entry = line.strip()
                if not entry or entry.startswith('#'):
                    continue

                entries = [x.strip() for x in entry.split() if x.strip()]
                if len(entries) == 1 and entries[0].lower().startswith('http'):
                    text = _get_url(entry)
                    _process_lines(text.split('\n'))
                    continue

                if len(entries) < 2:
                    continue

                rewrites.append(entries)

        with open(file_path, 'r') as f:
            text = f.read()

        _process_lines(text.split('\n'))
    except Exception as e:
        log.debug('DNS Rewrites Failed: {}'.format(file_path))
        log.exception(e)

    return rewrites
