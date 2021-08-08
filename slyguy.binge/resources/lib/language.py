from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    SHOW_CHNOS            = 30000
    ASK_USERNAME          = 30001
    ASK_PASSWORD          = 30002
    LOGIN_ERROR           = 30003
    LIVE_PANEL_ID_MISSING = 30004
    SELECT_PROFILE        = 30005
    LIVE_CHNO             = 30006
    PROFILE_ACTIVATED     = 30007

    FEATURED              = 30018
    SHOWS                 = 30019
    MOVIES                = 30020
    BINGE_LISTS           = 30021
    LIVE_CHANNELS         = 30022
    ASSET_ERROR           = 30023
    HEVC                  = 30024
    LOGIN_WITH            = 30025
    DEVICE_LINK           = 30026
    EMAIL_PASSWORD        = 30027
    DEVICE_LINK_STEPS     = 30028

    REFRESH_TOKEN_ERROR   = 30030
    SHOW_HERO_CONTENTS    = 30031
    TOKEN_ERROR           = 30032
    PAGE_ERROR            = 30033

_ = Language()