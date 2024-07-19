from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    LIVE_TV            = 30000
    SHOW_EPG           = 30001
    SHOW_CHNOS         = 30002
    LIVE_CHNO          = 30003
    CHANNEL_MODE       = 30004
    FREEVIEW_ONLY      = 30006
    FAST_ONLY          = 30007


_ = Language()
