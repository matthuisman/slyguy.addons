from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME      = 30001
    ASK_PASSWORD      = 30002
    HOME              = 30003
    LIVE_TV           = 30004
    SHOWS             = 30005
    MOVIES            = 30006
    SPORT             = 30007
    NEWS              = 30008
    CATEGORIES        = 30009
    RECENTLY_ADDED    = 30010
    ALL               = 30011
    FEATURED          = 30012
    SHOWS_LETTER      = 30013
    HIDE_SUGGESTED    = 30014
    FLATTEN_SEASONS   = 30015
    SUGGESTED         = 30016
    OLYMPICS          = 30017
    NO_VIDEO          = 30018

_ = Language()