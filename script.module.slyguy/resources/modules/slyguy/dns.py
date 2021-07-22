import os

import requests
from kodi_six import xbmc

from .log import log
from .mem_cache import cached
from .constants import ADDON_PROFILE, ADDON_ID, COMMON_ADDON

def get_dns_rewrites():
    rewrites = _load_rewrites(ADDON_PROFILE)

    if COMMON_ADDON.getAddonInfo('id') != ADDON_ID:
        rewrites.extend(_load_rewrites(COMMON_ADDON.getAddonInfo('profile')))

    if rewrites:
        log.debug('Rewrites Loaded: {}'.format(len(rewrites)))

    return rewrites

@cached(expires=60*5)
def _get_url(url):
    log.debug('Request DNS URL: {}'.format(url))
    return requests.get(url).text

def _load_rewrites(directory):
    rewrites = []

    file_path = os.path.join(xbmc.translatePath(directory), 'dns_rewrites.txt')
    if not os.path.exists(file_path):
        return rewrites

    try:
        def _process_lines(lines):
            for line in lines:
                entry = line.strip()
                if not entry:
                    continue

                try:
                    ip, pattern = entry.split(None, 1)
                except:
                    if entry.lower().startswith('http'):
                        text = _get_url(entry)
                        _process_lines(text.split('\n'))

                    continue

                pattern = pattern.strip()
                ip = ip.strip()
                if not pattern or not ip:
                    continue

                rewrites.append((pattern, ip))

        with open(file_path, 'r') as f:
            text = f.read()

        _process_lines(text.split('\n'))
    except Exception as e:
        raise
        log.debug('DNS Rewrites Failed: {}'.format(file_path))
        log.exception(e)

    return rewrites
