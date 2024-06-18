from time import time

from . import settings
from .constants import DONOR_URL, DONOR_CHECK_TIME, DONOR_TIMEOUT, COMMON_ADDON
from .util import get_kodi_string, set_kodi_string
from .log import log

KEY = '_slyguy_donor_{}'.format(COMMON_ADDON.getAddonInfo('version'))


def is_donor():
    return bool(int(get_kodi_string(KEY, 0)))


def check_donor(force=False):
    donor_id = settings.common_settings.get('donor_id')
    if not donor_id:
        if is_donor():
            _unset_donor()
            set_kodi_string(KEY, '')
        return

    _is_donor = get_kodi_string(KEY, None)
    _time = int(time())
    if not force and _is_donor is not None and _time < settings.common_settings.getInt('_last_donor_check', 0) + DONOR_CHECK_TIME:
        return bool(int(_is_donor))

    if _is_donor is None:
        _is_donor = settings.common_settings.get('_donor_id') == donor_id
    _is_donor = bool(int(_is_donor))

    try:
        from .session import Session
        result = Session().head(DONOR_URL.format(id=donor_id), log_url=DONOR_URL.format(id='xxxxx')).status_code == 200
    except:
        if _time > settings.common_settings.getInt('_last_donor_check', 0) + DONOR_TIMEOUT:
            result = False
        else:
            result = _is_donor
    else:
        settings.common_settings.setInt('_last_donor_check', _time)

    if result:
        if not is_donor():
            log.info('Welcome SlyGuy donor!')
        _set_donor()
        settings.common_settings.set('_donor_id', donor_id)
    else:
        _unset_donor()


def _set_donor():
    set_kodi_string(KEY, '1')
    set_kodi_string('_slyguy_donor', '1')


def _unset_donor():
    set_kodi_string(KEY, '0')
    set_kodi_string('_slyguy_donor', '0')
    settings.common_settings.remove('_donor_id')
