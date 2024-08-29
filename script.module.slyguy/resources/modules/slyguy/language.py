from kodi_six import xbmc

from slyguy.log import log
from slyguy.constants import ADDON, COMMON_ADDON


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


def addon_string(id, addon=ADDON):
    if id >= 30000:
        string = addon.getLocalizedString(id)
    else:
        string = xbmc.getLocalizedString(id)

    if not string:
        log.warning("LANGUAGE: Addon didn't return a string for id: {}".format(id))
        string = str(id)

    return string


class BaseLanguage(object):
    NO_UPDATES                  = 30001
    UPDATES_INSTALLED           = 30002
    UPDATES_AVAILABLE           = 30003
    ATMOS_LABEL                 = 30004
    PERSIST_CACHE               = 30006
    NO_LOG_ERRORS               = 30016
    LOG_ERRORS                  = 30017
    UPLOAD_LOG                  = 30018
    ARCH_CHANGED                = 30036
    VIDEO_MENUS                 = 30037

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
    IA_WV_INSTALL_OK            = 32022
    LOGIN                       = 32024
    LOGOUT                      = 32025
    SETTINGS                    = 32026
    LOGOUT_YES_NO               = 32027
    LOGIN_ERROR                 = 32028
    SEARCH                      = 32029
    SEARCH_FOR                  = 32030
    NO_RESULTS                  = 32031
    UNEXPECTED_ERROR            = 32032
    ERROR_DOWNLOADING_FILE      = 32033
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
    QUALITY_ASK = ASK = PLAY_FROM_ASK = 32055
    QUALITY_PARSE_ERROR         = 32056
    QUALITY_BAD_M3U8            = 32057
    WV_INSTALLED                = 32058
    MAX_BANDWIDTH               = 32059
    QUALITY_LOWEST              = 32060
    LIVE_HLS_REQUIRED           = 32062
    LIVE_PLAY_TYPE              = 32063
    PLAY_FROM_START             = 32064
    PLAY_FROM_LIVE              = 32065
    PLAY_FROM                   = 32067
    QUALITY_BITRATE             = 32068
    QUALITY_FPS                 = 32069
    SELECT_WV_VERSION           = 32070
    WV_UNKNOWN                  = 32071
    DEFAULT_LANGUAGE            = 32072
    QUALITY_HTTP_ERROR          = 32074
    IA_ANDROID_REINSTALL        = 32075
    GEO_ERROR                   = 32077
    SETUP_IPTV_MERGE            = 32079
    EPG_DAYS                    = 32080
    TV_EPG_CATEGORY             = 32081
    FORCE_EPG_SCRAPER           = 32082
    PROFILE_ACTIVATED           = 32083
    SELECT_PROFILE              = 32084
    GEO_COUNTRY_ERROR           = 32085
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
    NO_CONTEXT_METHOD           = 32120
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
    SELECT_QUALITY              = 32061

    # SETTINGS
    CODECS                      = 32153
    SUPPORTERS                  = 32138
    SUPPORTER_ONLY              = 32156
    WV_LEVEL_L1                 = 30009
    WV_LEVEL_L3                 = 30010
    HDCP_OFF                    = 30012
    HDCP_1                      = 30013
    HDCP_2_2                    = 30014
    HDCP_3_0                    = 30015
    MAX_WIDTH                   = 30025
    MAX_HEIGHT                  = 30026
    MAX_AUDIO_CHANNELS          = 30033
    IGNORE_DISPLAY_RESOLUTION   = 30022
    USE_IA_HLS_LIVE             = 32076
    USE_IA_HLS_VOD              = 32023
    AUDIO_WHITELIST             = 32086
    SUBS_WHITELIST              = 32087
    AUDIO_DESCRIPTION           = 32090
    SUBS_FORCED                 = 32088
    SUBS_NON_FORCED             = 32089
    H265                        = 30027
    VP9                         = 30038
    AV1                         = 30039
    HDR10                       = 30028
    DOLBY_VISION                = 30029
    DOLBY_ATMOS                 = 30030
    AC3                         = 30031
    EC3                         = 30032
    PROXY_ENABLED               = 30005
    WV_LEVEL                    = 30007
    HDCP_LEVEL                  = 30011
    DONOR_ID                    = 30020
    SHOW_NEWS                   = 30021
    FAST_UPDATES                = 30040
    KIOSK                       = 32078
    MENU_VIEW_SHOWS_SEASONS     = 30024
    VIDEO_VIEW_MEDIA            = 30023
    VIDEO_VIEW_MENUS            = 30037
    REINSTALL_WV                = 32021
    UPDATE_ADDONS               = 30000
    CHECK_LOG                   = 30019
    KID_LOCKDOWN                = 32104
    RESET_TO_DEFAULT            = 32157
    NOT_A_SUPPORTER             = 32158
    IP_MODE                     = 32159
    SKIP_NEXT_CHANNEL           = 30034
    SUPPORTER_HELP              = 32161
    CONFIRM_DISABLE_PROXY       = 32162
    CONFIRM_CHANGE_WV_LEVEL     = 32163
    CONFIRM_CHANGE_HDCP_LEVEL   = 32164
    QUALITY_SELECT_MODE         = 32165
    WELCOME_SUPPORTER           = 32166
    SUPPORTER_NOT_FOUND         = 32167
    INHERITED_SETTING           = 32168
    PREFER_IPV4                 = 32169
    PREFER_IPV6                 = 32170
    ONLY_IPV4                   = 32171
    ONLY_IPV6                   = 32172
    CONFIRM_CLEAR_BULK          = 32173
    MEDIA_DEFAULT               = 32174
    LIVE_TV                     = 32175
    SHOW_EPG                    = 32176
    SHOW_CHNOS                  = 32177
    CHANNEL_MODE                = 32178
    OTA_ONLY                    = 32179
    FAST_ONLY                   = 32180
    PROFILE_WITH_PIN            = 32181
    PROFILE_KIDS                = 32182
    ENTER_PIN                   = 32183
    API_ERROR                   = 32184
    INVALID_TOKEN               = 32185
    DEVICE_LOGIN_ERROR          = 32186
    PROVIDER_LOGIN              = 32187
    HOME                        = 32188
    SERIES                      = 32189
    MOVIES                      = 32190
    GOTO_SERIES                 = 32191
    ENABLE_CHAPTERS             = 32192
    DTSX                        = 32193
    PLAYER                      = 32194
    NETWORK                     = 32195
    INTERFACE                   = 32196
    SYSTEM                      = 32197
    ADVANCED                    = 32198
    GENERAL                     = 32199
    ALL                         = 32200
    QUALITY                     = 32201
    LANGUAGE                    = 32202
    DEFAULT                     = 32203
    YES                         = 32204
    NO                          = 32205
    DISABLED                    = 32206
    NO_LIMIT                    = 32207
    RESUME_FROM                 = 32208
    PLAY_FROM_BEGINNING         = 32209
    PLAYBACK_FAILED             = 32210
    AUTO                        = 32211
    TRAILER                     = 32212
    PLAY_NEXT                   = 32213
    QUEUE_ITEM                  = 32214
    RESET_ALL_SETTINGS          = 32215
    ARE_YOU_SURE                = 32216
    DNS_SERVER                  = 32217
    HELP                        = 32218
    PVR_LIVE_TV                 = 32219
    MERGE_NOT_SUPPORTED         = 32220
    TRAILER_CONTEXT_MENU        = 32221
    NOT_SET                     = 32222

    def __init__(self):
        self._addon_map = {}    
        for cls in self.__class__.mro():
            if cls is object:
                continue

            if cls != BaseLanguage:
                addon = ADDON
            else:
                addon = COMMON_ADDON

            for name in cls.__dict__:
                val = cls.__dict__[name]
                if isinstance(val, int) and val not in self._addon_map:
                    self._addon_map[val] = addon

    def __getattr__(self, name):
       # raise Exception("{} missing".format(name))
        return str(name)

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if not isinstance(attr, int):
            return attr

        return addon_string(attr, self._addon_map.get(attr, ADDON))

    def __call__(self, attr, *args, **kwargs):
        if isinstance(attr, int):
            attr = addon_string(attr, self._addon_map.get(attr, ADDON))

        return format_string(attr, *args, **kwargs)


_ = BaseLanguage()
