from . import settings
from .log import log
from .constants import KODI_VERSION, WV_LEVELS, WV_AUTO, WV_L1, WV_L3
from .util import get_kodi_string, set_kodi_string

def is_wv_secure():
    return get_kodi_string('wv_secure') == 'true'

def widevine_level():
    return get_kodi_string('wv_level')

def hdcp_level():
    return get_kodi_string('hdcp_level')

def set_drm_level():
    level = None
    hdcp = None
    wv_level = settings.common_settings.getEnum('wv_level', WV_LEVELS, default=WV_AUTO)

    if wv_level == WV_AUTO:
        if KODI_VERSION > 17:
            try:
                import xbmcdrm
                crypto = xbmcdrm.CryptoSession('edef8ba9-79d6-4ace-a3c8-27dcd51d21ed', 'AES/CBC/NoPadding', 'HmacSHA256')
                hdcp = crypto.GetPropertyString('hdcpLevel')
                level = crypto.GetPropertyString('securityLevel')
            except Exception as e:
                log.debug('Failed to obtain widevine level')
                log.exception(e)
    else:
        level = wv_level

    if not level:
        level = WV_L3

    if not hdcp:
        hdcp = '0'

    log.debug('Widevine Level ({}): {}'.format('auto' if wv_level == WV_AUTO else 'manual', level))
    log.debug('HDCP Level: {}'.format(hdcp))
    set_kodi_string('wv_level', level)
    set_kodi_string('hdcp_level', hdcp)
    set_kodi_string('wv_secure', 'true' if level == WV_L1 else 'false')
