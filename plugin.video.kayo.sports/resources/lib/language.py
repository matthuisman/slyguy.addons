from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME          = 30001
    ASK_PASSWORD          = 30002
    LOGIN_ERROR           = 30003
    ASSET_ERROR           = 30004
    SELECT_PROFILE        = 30005
    SHOW_CHNOS            = 30006
    SHOWS                 = 30007
    SPORTS                = 30008
    NO_STREAM             = 30009
    LIVE_CHNO             = 30010
    LIVE                  = 30011
    LIVE_PANEL_ID_MISSING = 30012
    SELECT_PROFILE        = 30013
    SHOW_HERO             = 30014

    HLS_REQUIRED          = 30025

    FEATURED              = 30027
    NEXT_PAGE             = 30028
    LIVE_CHANNELS         = 30029

    PROFILE_ACTIVATED     = 30031

    LOGIN_WITH            = 30042
    DEVICE_LINK           = 30043
    EMAIL_PASSWORD        = 30044
    DEVICE_LINK_STEPS     = 30045

    REFRESH_TOKEN_ERROR   = 30047
    PREFER_CDN            = 30048
    CDN_AKAMAI            = 30049
    CDN_CLOUDFRONT        = 30050
    TOKEN_ERROR           = 30051
    AUTO                  = 30052

_ = Language()
