from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    DEVICE_ID           = 30000
    DEVICE_LINK         = 30001
    CHANNEL             = 30003
    SERIES              = 30004
    DEVICE_LINK_STEPS   = 30005
    REQUEST_ERROR       = 30006
    SPORT               = 30008
    KIDS                = 30009
    STREAM_ERROR        = 30010
    API_ERROR           = 30011
    REFRESH_TOKEN_ERROR = 30012
    CHANNEL_NOT_FOUND   = 30013
    FLATTEN_SEASONS     = 30014
    LICENSE_COOLDOWN_ERROR = 30015
    WIDEVINE_ERROR      = 30016


_ = Language()
