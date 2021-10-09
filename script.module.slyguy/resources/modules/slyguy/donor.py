from . import settings
from .session import Session
from .constants import DONOR_URL, COMMON_ADDON
from .util import get_kodi_string, set_kodi_string

KEY = '_slyguy_donor_{}'.format(COMMON_ADDON.getAddonInfo('version'))

def check_donor():
    donor_id = settings.common_settings.get('donor_id')
    if not donor_id:
        return False

    result = Session().head(DONOR_URL.format(id=donor_id), attempts=1, log_url=DONOR_URL.format(id='xxxx')).status_code == 200

    if result:
        set_kodi_string(KEY, '1')
        set_kodi_string('_slyguy_donor', '1')
        return True

    settings.common_settings.set('donor_id', '')
    set_kodi_string(KEY, '0')
    set_kodi_string('_slyguy_donor', '0')
    return False

def is_donor():
    return int(get_kodi_string(KEY, 0))
