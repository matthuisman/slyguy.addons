from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    SHOW_GROUPS      = 30003
    MY_CHANNELS      = 30005
    ADD_MY_CHANNEL   = 30006
    DEL_MY_CHANNEL   = 30007
    MY_CHANNEL_ADDED = 30008
    CHANNEL_COUNT    = 30009
    SELECT_REGIONS   = 30010


_ = Language()
