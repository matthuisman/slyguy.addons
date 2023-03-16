import os

import requests
from kodi_six import xbmc

from .log import log
from .mem_cache import cached
from .constants import ADDON_PROFILE, ADDON_ID, COMMON_ADDON

def get_dns_rewrites(dns_rewrites=None):
    rewrites = _load_rewrites(ADDON_PROFILE)

    if COMMON_ADDON.getAddonInfo('id') != ADDON_ID:
        rewrites.extend(_load_rewrites(COMMON_ADDON.getAddonInfo('profile')))

    if dns_rewrites:
        rewrites.extend(dns_rewrites)

    # add some defaults that are often blocked by networkwide dns
    rewrites.extend([
        ['r:https://cloudflare-dns.com/dns-query', 'dai.google.com'],
        ['r:https://cloudflare-dns.com/dns-query', 'slyguy.uk'],
        ['r:https://cloudflare-dns.com/dns-query', 'i.mjh.nz'],
    ])

    if rewrites:
        log.debug('Rewrites Loaded: {}'.format(len(rewrites)))

    return rewrites

@cached(expires=60*5)
def _get_url(url):
    log.debug('Request DNS URL: {}'.format(url))
    return requests.get(url).text

def _load_rewrites(directory):
    rewrites = []

    file_names = [
        'urls.txt',
        'dns_rewrites.txt', #legacy
    ]

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
