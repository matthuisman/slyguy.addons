from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    SHOW_CHNOS            = 30000
    LOGIN_ERROR           = 30003
    LIVE_PANEL_ID_MISSING = 30004
    SELECT_PROFILE        = 30005
    LIVE_CHNO             = 30006
    PROFILE_ACTIVATED     = 30007
    SHOW_EPG              = 30008

    FEATURED              = 30018
    SHOWS                 = 30019
    MOVIES                = 30020
    BINGE_LISTS           = 30021
    LIVE_CHANNELS         = 30022
    ASSET_ERROR           = 30023
    HEVC                  = 30024

    REFRESH_TOKEN_ERROR   = 30030
    SHOW_HERO_CONTENTS    = 30031
    TOKEN_ERROR           = 30032
    PAGE_ERROR            = 30033

    PREFER_CDN            = 30048
    CDN_AKAMAI            = 30049
    CDN_CLOUDFRONT        = 30050
    CDN_LUMEN             = 30051
    AUTO                  = 30052

_ = Language()
