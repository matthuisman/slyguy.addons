from time import time

import requests

from . import settings
from .constants import DONOR_URL, DONOR_CHECK_TIME, DONOR_TIMEOUT, COMMON_ADDON
from .util import get_kodi_string, set_kodi_string
from .log import log

KEY = '_slyguy_donor_{}'.format(COMMON_ADDON.getAddonInfo('version'))

def is_donor(force=False):
    donor_id = settings.common_settings.get('donor_id')
    if not donor_id:
        return False

    is_donor = get_kodi_string(KEY, None)
    _time = int(time())
    if not force and is_donor is not None and _time < settings.common_settings.getInt('_last_donor_check', 0) + DONOR_CHECK_TIME:
        return bool(int(is_donor))

    if is_donor is None:
        is_donor = '0'
    is_donor = bool(int(is_donor))

    try:
        log.debug('Requesting: {}'.format(DONOR_URL.format(id='xxxxx')))
        result = requests.head(DONOR_URL.format(id=donor_id)).status_code == 200
    except:
        if _time > settings.common_settings.getInt('_last_donor_check', 0) + DONOR_TIMEOUT:
            result = False
        else:
            return is_donor

    settings.common_settings.setInt('_last_donor_check', _time)

    if result:
        set_kodi_string(KEY, '1')
        set_kodi_string('_slyguy_donor', '1')
        if not is_donor:
            log.info('Welcome SlyGuy donor!')
        return True
    else:
        set_kodi_string(KEY, '0')
        set_kodi_string('_slyguy_donor', '0')
        return False
