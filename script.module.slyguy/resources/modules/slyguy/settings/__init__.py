import os
import re
from time import time

from slyguy import dialog
from slyguy.language import _
from slyguy.log import log
from slyguy.constants import *
from slyguy.util import get_kodi_string, set_kodi_string

from .types import BaseSettings, Bool, Dict, Number, Text, Enum, Categories, Action


WV_AUTO = -1
WV_L1 = 1
WV_L2 = 2
WV_L3 = 3
WV_UUID = 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed'
# List of system ids that use fake L1
WV_FAKE_L1 = ['7011','6077']

HDCP_AUTO = -1
HDCP_NONE = 0
HDCP_1 = 10
HDCP_2_2 = 22
HDCP_3_0 = 30


class IPMode:
    SYSTEM_DEFAULT = 'system_default'
    PREFER_IPV4 = 'prefer_ipv4'
    PREFER_IPV6 = 'prefer_ipv6'
    ONLY_IPV4 = 'only_ipv4'
    ONLY_IPV6 = 'only_ipv6'


def is_donor():
    return bool(settings.DONOR_ID_CHK.value and settings.DONOR_ID_CHK.value == settings.DONOR_ID.value)


def _set_donor(donor_id):
    set_kodi_string('_slyguy_donor', '1')
    settings.set('donor_id_chk', donor_id)
    set_trailer_context()


def _unset_donor():
    set_kodi_string('_slyguy_donor', '0')
    settings.remove('donor_id_chk')
    set_trailer_context()


def is_wv_secure():
    return widevine_level() == WV_L1


def req_wv_level(level):
    return widevine_level() <= level


def req_hdcp_level(level):
    return hdcp_level() >= level


def widevine_level():
    wv_level = settings.WV_LEVEL.value
    if wv_level == WV_AUTO:
        return int(get_kodi_string('wv_level', WV_L3))
    else:
        return wv_level


def hdcp_level():
    hdcp_level = settings.HDCP_LEVEL.value
    if hdcp_level == HDCP_AUTO:
        return int(get_kodi_string('hdcp_level', HDCP_NONE))
    else:
        return hdcp_level


def set_trailer_context():
    if settings.TRAILER_CONTEXT_MENU.value:
        set_kodi_string('_slyguy_trailer_context_menu', '1')
    else:
        set_kodi_string('_slyguy_trailer_context_menu', '0')


def check_donor(force=False):
    if not settings.DONOR_ID.value:
        _unset_donor()
        return

    _time = int(time())
    if not force and _time < settings.getInt('last_donor_check', 0) + DONOR_CHECK_TIME:
        return is_donor()

    try:
        from slyguy.session import Session
        result = Session().head(DONOR_URL.format(id=settings.DONOR_ID.value), log_url=DONOR_URL.format(id='xxxxx')).status_code == 200
    except Exception as e:
        log.warning("Failed to check donor id due to: {}".format(e))
        if _time > settings.getInt('last_donor_check', 0) + DONOR_TIMEOUT:
            result = False
        else:
            log.debug("Using previous supporter status")
            result = is_donor()
    else:
        settings.setInt('last_donor_check', _time)

    log.debug('SlyGuy Supporter: {}'.format(result))
    if result:
        _set_donor(settings.DONOR_ID.value)
    else:
        _unset_donor()


def set_drm_level(*args, **kwargs):
    wv_level = settings.WV_LEVEL.value
    hdcp_level = settings.HDCP_LEVEL.value

    wv_mode = 'manual'
    hdcp_mode = 'manual'

    if wv_level == WV_AUTO:
        wv_mode = 'auto'
        wv_level = None

    if hdcp_level == HDCP_AUTO:
        hdcp_mode = 'auto'
        hdcp_level = None

    if not wv_level or not hdcp_level:
        if KODI_VERSION > 17:
            try:
                import xbmcdrm
                crypto = xbmcdrm.CryptoSession(WV_UUID, 'AES/CBC/NoPadding', 'HmacSHA256')

                if not wv_level:
                    wv_level = crypto.GetPropertyString('securityLevel')
                    if wv_level:
                        wv_level = int(wv_level.lower().lstrip('l'))

                        try:
                            system_id = crypto.GetPropertyString('systemId')
                        except:
                            system_id = 'N/A'

                        log.info("Widevine System ID: {}".format(system_id))
                        if wv_level == WV_L1 and system_id in WV_FAKE_L1:
                            log.info('Detected fake L1 System ID {}. Downgrading to L3'.format(system_id))
                            wv_level = WV_L3

                if not hdcp_level:
                    hdcp_level = crypto.GetPropertyString('hdcpLevel')
                    if hdcp_level:
                        hdcp_level = re.findall('\\d+\\.\\d+', hdcp_level)
                        hdcp_level = int(float(hdcp_level[0])*10) if hdcp_level else None

            except Exception as e:
                log.debug('Failed to obtain crypto config')
                log.exception(e)

        if not wv_level:
            wv_mode = 'fallback'
            wv_level = WV_L3

        if not hdcp_level:
            hdcp_mode = 'fallback'
            hdcp_level = HDCP_NONE

    set_kodi_string('wv_level', wv_level)
    set_kodi_string('hdcp_level', hdcp_level)

    log.info('Widevine Level ({}): {}'.format(wv_mode, wv_level))
    log.info('HDCP Level ({}): {}'.format(hdcp_mode, hdcp_level/10.0))


class Donor(Text):
    def __init__(self, *args, **kwargs):
        super(Donor, self).__init__(*args, **kwargs)
        self._after_save = self.after_save
        self._after_clear = self.after_clear

    def after_save(self, value):
        check_donor(force=True)
        from slyguy import gui
        if is_donor():
            gui.notification(_.WELCOME_SUPPORTER)
        else:
            gui.notification(_.SUPPORTER_NOT_FOUND)

    def after_clear(self):
        _unset_donor()

    @property
    def label(self):
        value = self.value
        value = u"{}{}".format(value[0:2], '*'*(len(value)-2))

        if not value:
            value = _.NOT_A_SUPPORTER
        elif self.can_clear():
            value = _(value, _bold=True)

        if is_donor():
            value = _(value, _color='green')
        else:
            value = _(value, _color='red')

        label = u'{}: {}'.format(self._label, value)
        return label

    @property
    def description(self):
        if is_donor():
            return _.WELCOME_SUPPORTER
        elif self.value:
            return u'{}\n\n{}'.format(_(_.SUPPORTER_NOT_FOUND, _color='red'), _.SUPPORTER_HELP)
        else:
            return _.SUPPORTER_HELP


class CommonSettings(BaseSettings):
    # PLAYER / QUALITY
    QUALITY_MODE = Enum('quality_mode', legacy_ids=['default_quality'], label=_.QUALITY_SELECT_MODE, default=QUALITY_ASK, disabled_value=QUALITY_SKIP, enable=is_donor, disabled_reason=_.SUPPORTER_ONLY,
        options=[[_.QUALITY_ASK, QUALITY_ASK], [_.QUALITY_BEST, QUALITY_BEST], [_.QUALITY_LOWEST, QUALITY_LOWEST], [_.QUALITY_SKIP, QUALITY_SKIP]],
        owner=COMMON_ADDON_ID, category=Categories.PLAYER_QUALITY)
    MAX_BANDWIDTH = Number('max_bandwidth', default_label=_.NO_LIMIT, owner=COMMON_ADDON_ID, visible=lambda: CommonSettings.QUALITY_MODE.value != QUALITY_SKIP, category=Categories.PLAYER_QUALITY)
    MAX_WIDTH = Number('max_width', default_label=_.NO_LIMIT, owner=COMMON_ADDON_ID, visible=lambda: CommonSettings.QUALITY_MODE.value != QUALITY_SKIP, category=Categories.PLAYER_QUALITY)
    MAX_HEIGHT = Number('max_height', default_label=_.NO_LIMIT, owner=COMMON_ADDON_ID, visible=lambda: CommonSettings.QUALITY_MODE.value != QUALITY_SKIP, category=Categories.PLAYER_QUALITY)
    IGNORE_DISPLAY_RESOLUTION = Bool('ignore_display_resolution', default=True, owner=COMMON_ADDON_ID, visible=lambda: CommonSettings.QUALITY_MODE.value != QUALITY_SKIP, category=Categories.PLAYER_QUALITY)

    # PLAYER / CODECS
    H265 = Bool('h265', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    VP9 = Bool('vp9', owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    AV1 = Bool('av1', owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    HDR10 = Bool('hdr10', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    DOLBY_VISION = Bool('dolby_vision', owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    DOLBY_ATMOS = Bool('dolby_atmos', owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    DTSX = Bool('dtsx', owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    AC3 = Bool('ac3', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    EC3 = Bool('ec3', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)
    MAX_AUDIO_CHANNELS = Number('max_audio_channels', legacy_ids=['max_channels'], default_label=_.NO_LIMIT, owner=COMMON_ADDON_ID, category=Categories.PLAYER_CODECS)

    # PLAYER / LANGUAGE
    AUDIO_WHITELIST = Text('audio_whitelist', default_label=_.ALL, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    SUBS_WHITELIST = Text('subs_whitelist', default_label=_.ALL, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    AUDIO_DESCRIPTION = Bool('audio_description', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    SUBS_FORCED = Bool('subs_forced', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    SUBS_NON_FORCED = Bool('subs_non_forced', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    DEFAULT_LANGUAGE = Text('default_language', default_label=_.MEDIA_DEFAULT, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)
    DEFAULT_SUBTITLE = Text('default_subtitle', default_label=_.MEDIA_DEFAULT, owner=COMMON_ADDON_ID, category=Categories.PLAYER_LANGUAGE)

    # PLAYER / ADVANCED
    REINSTALL_WV = Action("RunPlugin(plugin://{}/?_=_ia_install)".format(COMMON_ADDON_ID), visible="!system.platform.android", category=Categories.PLAYER_ADVANCED)
    LIVE_PLAY_TYPE = Enum('live_play_type', options=[[_.PLAY_FROM_ASK, PLAY_FROM_ASK], [_.PLAY_FROM_LIVE_CONTEXT, PLAY_FROM_LIVE], [_.PLAY_FROM_BEGINNING, PLAY_FROM_START]],
                    loop=True, default=PLAY_FROM_ASK, owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)
    USE_IA_HLS_LIVE = Bool('use_ia_hls_live', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)
    USE_IA_HLS_VOD = Bool('use_ia_hls_vod', default=True, owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)
    PROXY_ENABLED = Bool('proxy_enabled', default=True, before_save=lambda val: val or dialog.yes_no(_.CONFIRM_DISABLE_PROXY), owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)
    WV_LEVEL = Enum('wv_level', before_save=lambda val: settings.WV_LEVEL.value != WV_AUTO or dialog.yes_no(_.CONFIRM_CHANGE_WV_LEVEL), after_save=set_drm_level,
                    options=[[_.AUTO, WV_AUTO], [_.WV_LEVEL_L1, WV_L1], [_.WV_LEVEL_L3, WV_L3]],
                    loop=True, default=WV_AUTO, owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)
    HDCP_LEVEL = Enum('hdcp_level', before_save=lambda val: settings.HDCP_LEVEL.value != HDCP_AUTO or dialog.yes_no(_.CONFIRM_CHANGE_HDCP_LEVEL), after_save=set_drm_level,
                      options=[[_.AUTO, HDCP_AUTO], [_.HDCP_OFF, HDCP_NONE], [_.HDCP_1, HDCP_1], [_.HDCP_2_2, HDCP_2_2], [_.HDCP_3_0, HDCP_3_0]], 
                      loop=True, default=HDCP_AUTO, owner=COMMON_ADDON_ID, category=Categories.PLAYER_ADVANCED)

    # NETWORK
    VERIFY_SSL = Bool('verify_ssl', default=True, owner=COMMON_ADDON_ID, category=Categories.NETWORK)
    HTTP_TIMEOUT = Number('http_timeout', default=15, owner=COMMON_ADDON_ID, category=Categories.NETWORK)
    HTTP_RETRIES = Number('http_retries', default=1, owner=COMMON_ADDON_ID, category=Categories.NETWORK)
    PROXY_SERVER = Text('proxy_server', owner=COMMON_ADDON_ID, enable=is_donor, disabled_reason=_.SUPPORTER_ONLY, default_label=_.DEFAULT, category=Categories.NETWORK)
    DNS_SERVER = Text('dns_server', owner=COMMON_ADDON_ID, enable=is_donor, disabled_reason=_.SUPPORTER_ONLY, default_label=_.DEFAULT, category=Categories.NETWORK)
    IP_MODE = Enum('ip_mode', options=[[_.PREFER_IPV4, IPMode.PREFER_IPV4], [_.PREFER_IPV6, IPMode.PREFER_IPV6], [_.ONLY_IPV4, IPMode.ONLY_IPV4], [_.ONLY_IPV6, IPMode.ONLY_IPV6]],
                    default=IPMode.PREFER_IPV4, owner=COMMON_ADDON_ID, category=Categories.NETWORK, enable=is_donor, disabled_reason=_.SUPPORTER_ONLY)

    # INTERFACE
    BOOKMARKS = Bool('bookmarks', default=True, owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    KID_LOCKDOWN = Bool('kid_lockdown', default=False, owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    KIOSK = Bool('kiosk', owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    PAGINATION_MULTIPLIER = Number('pagination_multiplier', default=1, owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    MENU_VIEW_SHOWS_SEASONS = Bool('menu_view_shows_seasons', owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    VIDEO_VIEW_MEDIA = Bool('video_view_media', owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    VIDEO_VIEW_MENUS = Bool('video_view_menus', owner=COMMON_ADDON_ID, category=Categories.INTERFACE)
    SHOW_NEWS = Bool('show_news', default=True, enable=is_donor, disabled_value=True, disabled_reason=_.SUPPORTER_ONLY, override=False, owner=COMMON_ADDON_ID, category=Categories.INTERFACE)

    # PVR
    SETUP_IPTV_MERGE = Action("RunPlugin(plugin://{}/?_=_setup_merge)".format(ADDON_ID), owner=COMMON_ADDON_ID, visible=lambda: os.path.exists(os.path.join(ADDON_PATH, MERGE_SETTING_FILE)), category=Categories.PVR_LIVE_TV)
    SKIP_NEXT_CHANNEL = Bool('skip_next_channel', default=False, owner=COMMON_ADDON_ID, visible=lambda: ADDON_ID == COMMON_ADDON_ID or os.path.exists(os.path.join(ADDON_PATH, MERGE_SETTING_FILE)), category=Categories.PVR_LIVE_TV)
    EPG_DAYS = Number('epg_days', default=3, lower_limit=1, upper_limit=7, owner=COMMON_ADDON_ID, visible=lambda: ADDON_ID == COMMON_ADDON_ID or os.path.exists(os.path.join(ADDON_PATH, MERGE_SETTING_FILE)), category=Categories.PVR_LIVE_TV)

    # SYSTEM
    FAST_UPDATES = Bool('fast_updates', default=True, enable=is_donor, disabled_value=False, disabled_reason=_.SUPPORTER_ONLY, override=False, owner=COMMON_ADDON_ID, category=Categories.SYSTEM)
    TRAILER_CONTEXT_MENU = Bool('trailer_context_menu', default=True, enable=is_donor, after_save=lambda val:set_trailer_context(),
        after_clear=set_trailer_context, disabled_value=False, disabled_reason=_.SUPPORTER_ONLY, override=False, owner=COMMON_ADDON_ID, category=Categories.SYSTEM)
    UPDATE_ADDONS = Action("RunPlugin(plugin://{}/?_=update_addons)".format(COMMON_ADDON_ID), enable=is_donor, disabled_reason=_.SUPPORTER_ONLY, owner=COMMON_ADDON_ID, category=Categories.SYSTEM)
    CHECK_LOG = Action("RunPlugin(plugin://{}/?_=check_log)".format(COMMON_ADDON_ID), owner=COMMON_ADDON_ID, category=Categories.SYSTEM)

    # ROOT
    DONOR_ID = Donor('donor_id', override=False, confirm_clear=True, owner=COMMON_ADDON_ID, category=Categories.ROOT)

    # HIDDEN
    DONOR_ID_CHK = Text('donor_id_chk', visible=False, override=False, owner=COMMON_ADDON_ID)
    ADDONS_MD5 = Text('addon_md5', visible=False, override=False, owner=COMMON_ADDON_ID)
    LAST_DONOR_CHECK = Number('last_donor_check', visible=False, override=False, owner=COMMON_ADDON_ID)
    LAST_NEWS_CHECK = Number('last_news_check', visible=False, override=False, owner=COMMON_ADDON_ID)
    LAST_NEWS_ID = Text('last_news_id', visible=False, override=False, owner=COMMON_ADDON_ID)
    PROXY_PORT = Number('proxy_port', default=DEFAULT_PORT, visible=False, override=False, owner=COMMON_ADDON_ID)
    PROXY_PATH = Text('proxy_path', visible=False, override=False, owner=COMMON_ADDON_ID)
    UPDATES = Dict('updates', visible=False, override=False, owner=COMMON_ADDON_ID)
    NEWS = Dict('news', visible=False, override=False, owner=COMMON_ADDON_ID)
    LAST_UPDATES_CHECK = Number('last_updates_check', visible=False, override=False, owner=COMMON_ADDON_ID)
    WV_LAST_CHECK = Number('wv_last_check', visible=False, override=False, owner=COMMON_ADDON_ID)
    WV_LATEST_HASH = Text('wv_latest_hash', visible=False, override=False, owner=COMMON_ADDON_ID)
    MAC = Number('mac', visible=False, override=False, owner=COMMON_ADDON_ID)
    ARCH = Text('arch', visible=False, override=False, owner=COMMON_ADDON_ID)


settings = CommonSettings(COMMON_ADDON_ID)
