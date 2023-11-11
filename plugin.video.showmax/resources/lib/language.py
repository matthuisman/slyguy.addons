from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME      = 30000
    ASK_PASSWORD      = 30001
    SERIES            = 30002
    MOVIES            = 30003
    KIDS              = 30004
    SEASON_NUMBER     = 30005
    EPISODE_NUMBER    = 30006
    H264              = 30007
    LANG_ENG          = 30008
    LANG_POL          = 30009
    LANG_AFR          = 30010
    H265              = 30011
    AUDIO_LANGUAGE    = 30012
    VP9               = 30013
    SELECT_LANG       = 30014

_ = Language()