from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LIVE_TV              = 30002
    LOCAL_CHANNEL_IP     = 30003

    DEVICE_ID            = 30008
    OUT_OF_REGION        = 30009
    SHOWS                = 30011
    EPISODE_COUNT        = 30012
    CLIPS_COUNT          = 30013
    SEASON               = 30014
    CLIPS                = 30015
    MOVIES               = 30016
    A_Z                  = 30017
    POPULAR              = 30018
    FEATURED             = 30019
    H265                 = 30020
    ENABLE_4K            = 30021
    DOLBY_VISION         = 30022

    EC3_ENABLED          = 30024
    AC3_ENABLED          = 30025
    PARTNER_LOGIN        = 30026
    SELECT_PARTNER       = 30027
    IGNORE_SUBS          = 30028
    REFRESH_TOKEN_ERROR  = 30029

_ = Language()
