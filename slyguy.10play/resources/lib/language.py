from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    STATE           = 30000
    AUTO            = 30001
    NSW             = 30002
    VIC             = 30003
    QLD             = 30004
    WA              = 30005
    SA              = 30006
    LIVE_TV         = 30007
    ALL             = 30008
    SHOWS_LETTER    = 30009
    ZERO_NINE       = 30010
    SHOWS           = 30011
    FLATTEN_SEASONS = 30012
    HIDE_EXTRAS     = 30013
    CATEGORIES      = 30014
    FEATURED        = 30015

_ = Language()
