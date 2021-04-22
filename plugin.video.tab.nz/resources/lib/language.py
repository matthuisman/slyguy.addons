from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    TRACKSIDE_1     = 30001
    TRACKSIDE_2     = 30002
    LIVE_EVENTS     = 30003
    ASK_USERNAME    = 30004
    ASK_PASSWORD    = 30005
    NO_EVENTS       = 30006
    TRACKSIDE_RADIO = 30007
    AUTH_ERROR      = 30008
    GEO_ERROR       = 30009
    SAVE_PASSWORD   = 30010

_ = Language()