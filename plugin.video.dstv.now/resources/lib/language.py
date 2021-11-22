from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    DEVICE_ID           = 30000
    DEVICE_LINK         = 30001
    LIVE_TV             = 30002
    CHANNEL             = 30003
    SERIES              = 30004
    DEVICE_LINK_STEPS   = 30005
    REQUEST_ERROR       = 30006
    MOVIES              = 30007
    SPORT               = 30008
    KIDS                = 30009
    STREAM_ERROR        = 30010
    API_ERROR           = 30011
    REFRESH_TOKEN_ERROR = 30012
    CHANNEL_NOT_FOUND   = 30013
    FLATTEN_SEASONS     = 30014
    USE_CACHED_ZA       = 30015

_ = Language()
