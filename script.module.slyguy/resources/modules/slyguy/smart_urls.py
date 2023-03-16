import os

from kodi_six import xbmc

from .log import log
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

def _load_rewrites(directory):
    file_path = os.path.join(xbmc.translatePath(directory), 'urls.txt')
    if not os.path.exists(file_path):
        return []

    rewrites = []
    try:
        with open(file_path, 'r') as f:
            text = f.read()

        for line in text.split('\n'):
            entry = line.strip()
            if not entry or entry.startswith('#'):
                continue

            entries = [x.strip() for x in entry.split() if x.strip()]
            if len(entries) < 2:
                continue

            rewrites.append(entries)
    except Exception as e:
        log.debug('DNS Rewrites Failed: {}'.format(file_path))
        log.exception(e)

    return rewrites
