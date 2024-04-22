from kodi_six import xbmc

from .log import log
from .constants import ADDON, COMMON_ADDON

def format_string(string, *args, **kwargs):
    style = {}

    if kwargs:
        for key in list(kwargs.keys()):
            if key.startswith('_'):
                style[key.lstrip('_')] = kwargs.pop(key)

    if args or kwargs:
        try:
            string = string.format(*args, **kwargs)
        except Exception as e:
            log.debug('failed to format string: {} ({})'.format(string, e))

    if not style:
        return string

    if style.get('strip'):
        string = string.strip()

    if style.get('label'):
        style['bold'] = True
        string = u'~ {} ~'.format(string)

    if style.get('bold'):
        string = u'[B]{}[/B]'.format(string)

    if 'color' in style:
        string = u'[COLOR {}]{}[/COLOR]'.format(style['color'], string)

    return string

def addon_string(id):
    if id >= 32000:
        string = COMMON_ADDON.getLocalizedString(id)
    elif id >= 30000:
        string = ADDON.getLocalizedString(id)
    else:
        string = xbmc.getLocalizedString(id)

    if not string:
        log.warning("LANGUAGE: Addon didn't return a string for id: {}".format(id))
        string = str(id)

    return string

class BaseLanguage(object):
    PLUGIN_LOGIN_REQUIRED       = 32000
    PLUGIN_NO_DEFAULT_ROUTE     = 32001
    PLUGIN_RESET_YES_NO         = 32002
    PLUGIN_RESET_OK             = 32003
    PLUGIN_CACHE_REMOVED        = 32004
    PLUGIN_CONTEXT_CLEAR_CACHE  = 32005
    ROUTER_NO_FUNCTION          = 32006
    ROUTER_NO_URL               = 32007
    ADDON_REQUIRED              = 32008
    IA_UWP_ERROR                = 32009
    IA_KODI18_REQUIRED          = 32010
    IA_AARCH64_ERROR            = 32011
    IA_NOT_SUPPORTED            = 32012
    NO_BRIGHTCOVE_SRC           = 32013
    IA_DOWNLOADING_FILE         = 32014
    IA_WIDEVINE_DRM             = 32015
    IA_ERROR_INSTALLING         = 32016
    USE_CACHE                   = 32017
    INPUTSTREAM_SETTINGS        = 32018
    CLEAR_DATA                  = 32019
    PLUGIN_ERROR                = 32020
    INSTALL_WV_DRM              = 32021
    IA_WV_INSTALL_OK            = 32022
    IA_HLS_FOR_VOD              = 32023
    LOGIN                       = 32024
    LOGOUT                      = 32025
    SETTINGS                    = 32026
    LOGOUT_YES_NO               = 32027
    LOGIN_ERROR                 = 32028
    SEARCH                      = 32029
    SEARCH_FOR                  = 32030
    NO_RESULTS                  = 32031
    PLUGIN_EXCEPTION            = 32032
    ERROR_DOWNLOADING_FILE      = 32033
    GENERAL                     = 32034
    PLAYBACK                    = 32035
    ADVANCED                    = 32036
    VERIFY_SSL                  = 32037
    SELECT_IA_VERSION           = 32038
    SERVICE_DELAY               = 32039
    MD5_MISMATCH                = 32040
    NO_ITEMS                    = 32041
    MIGRATE_ADDON_NOT_FOUND     = 32042
    QUALITY_BEST                = 32043
    HTTP_TIMEOUT                = 32044
    HTTP_RETRIES                = 32045
    IA_WEBOS_ERROR              = 32046

    QUALITY_SKIP                = 32048
    NO_AUTOPLAY_FOUND           = 32049
    CONFIRM_MIGRATE             = 32050
    MIGRATE_OK                  = 32051
    NO_ERROR_MSG                = 32052
    MULTI_BASEURL_WARNING       = 32053
    QUALITY_CUSTOM              = 32054
    QUALITY_ASK                 = 32055
    QUALITY_PARSE_ERROR         = 32056
    QUALITY_BAD_M3U8            = 32057
    WV_INSTALLED                = 32058
    MAX_BANDWIDTH               = 32059
    QUALITY_LOWEST              = 32060
    PLAYBACK_QUALITY            = 32061
    LIVE_HLS_REQUIRED           = 32062
    PLAY_DEFAULT_ACTION         = 32063
    PLAY_FROM_START             = 32064
    PLAY_FROM_LIVE              = 32065
    PLAY_FROM_ASK               = 32066
    PLAY_FROM                   = 32067
    QUALITY_BITRATE             = 32068
    QUALITY_FPS                 = 32069
    SELECT_WV_VERSION           = 32070
    WV_UNKNOWN                  = 32071
    DEFAULT_LANGUAGE            = 32072
    DISABLED                    = 32073
    QUALITY_HTTP_ERROR          = 32074
    IA_ANDROID_REINSTALL        = 32075
    IA_HLS_FOR_LIVE             = 32076
    GEO_ERROR                   = 32077
    KIOSK_MODE                  = 32078
    SETUP_IPTV_MERGE            = 32079
    EPG_DAYS                    = 32080
    TV_EPG_CATEGORY             = 32081
    FORCE_EPG_SCRAPER           = 32082
    PROFILE_ACTIVATED           = 32083
    SELECT_PROFILE              = 32084
    GEO_COUNTRY_ERROR           = 32085
    AUDIO_ALLOW_LIST            = 32086
    SUBTITLE_ALLOW_LIST         = 32087
    INCLUDE_FORCED              = 32088
    INCLUDE_NON_FORCED          = 32089
    INCLUDE_CC                  = 32090
    ADD_PROFILE                 = 32091
    DELETE_PROFILE              = 32092
    RANDOM_AVATAR               = 32093
    SELECT_AVATAR               = 32094
    SELECT_DELETE_PROFILE       = 32095
    DELETE_PROFILE_INFO         = 32096
    DELTE_PROFILE_HEADER        = 32097
    PROFILE_DELETED             = 32098
    AVATAR_USED                 = 32099
    KIDS_PROFILE_INFO           = 32100
    KIDS_PROFILE                = 32101
    PROFILE_NAME                = 32102
    PROFILE_NAME_TAKEN          = 32103
    KIDS_MODE_SETTING           = 32104
    IA_VERSION_REQUIRED         = 32105
    IA_ARMV6_ERROR              = 32106
    IA_IOS_ERROR                = 32107
    NEXT_PAGE                   = 32108
    JSON_ERROR                  = 32109
    NO_RESPONSE_ERROR           = 32110
    BOOKMARKS                   = 32111
    ADD_BOOKMARK                = 32112
    DELETE_BOOKMARK             = 32113
    BOOKMARK_ADDED              = 32114
    MOVE_UP                     = 32115
    MOVE_DOWN                   = 32116
    RENAME_BOOKMARK             = 32117
    XZ_ERROR                    = 32118
    INSTALLING_APT_IA           = 32119

    DEFAULT_SUBTITLE            = 32121
    WV_REVOKED                  = 32122
    WV_REVOKED_CONFIRM          = 32123
    WV_FAILED                   = 32124
    IA_TVOS_ERROR               = 32125
    NEW_SEARCH                  = 32126
    REMOVE_SEARCH               = 32127
    NEWS_HEADING                = 32128

    PLAY_FROM_LIVE_CONTEXT      = 32130
    ASK_EMAIL                   = 32131
    ASK_PASSWORD                = 32132
    DEVICE_CODE                 = 32133
    EMAIL_PASSWORD              = 32134
    DEVICE_LINK_STEPS           = 32135
    WV_UNSUPPORTED_OS           = 32136
    WV_UNSUPPORTED_OS_CONFIRM   = 32137
    DONATIONS                   = 32138
    LOOK_AND_FEEL               = 32139
    DONATE_HEADER               = 32140
    SEASON                      = 32141
    IA_LINUX_MISSING            = 32142
    PAGINATION_MULTIPLIER       = 32143
    PLAYBACK_FAILED_CHECK_LOG   = 32144
    WV_ISSUES                   = 32145
    WV_ISSUES_CONFIRM           = 32146
    PROXY_SERVER                = 32147
    TRAILER_NOT_FOUND           = 32148
    CONNECTION_ERROR            = 32149
    CONNECTION_ERROR_PROXY      = 32150
    UPDATES_REQUIRED            = 32151

    # Kodi strings
    LANGUAGE                    = 304
    RESUME_FROM                 = 12022
    PLAY_FROM_BEGINNING         = 12021
    PLAYBACK_FAILED             = 16026
    AUTO                        = 16316
    TRAILER                     = 20410

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if not isinstance(attr, int):
            return attr

        return addon_string(attr)

    def __call__(self, string, *args, **kwargs):
        if isinstance(string, int):
            string = addon_string(string)

        return format_string(string, *args, **kwargs)

_ = BaseLanguage()
