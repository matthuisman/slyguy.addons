from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    REGION_IP            = 30003
    LIVE                 = 30004
    DEVICE_ID            = 30008
    OUT_OF_REGION        = 30009
    SHOWS                = 30011
    CLIPS                = 30015
    A_Z                  = 30017
    POPULAR              = 30018
    FEATURED             = 30019
    PARTNER_LOGIN        = 30026
    SELECT_PARTNER       = 30027
    IGNORE_SUBS          = 30028
    REFRESH_TOKEN_ERROR  = 30029
    SYNC_PLAYBACK        = 30030


_ = Language()
