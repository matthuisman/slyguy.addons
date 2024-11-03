from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    REGION           = 30002
    SELECT_REGIONS   = 30005
    CHANNEL_COUNT    = 30006
    NO_REGIONS       = 30007
    MY_CHANNELS      = 30008
    ADD_MY_CHANNEL   = 30009
    DEL_MY_CHANNEL   = 30010
    MY_CHANNEL_ADDED = 30011
    SHOW_GROUPS      = 30012
    SHOW_COUNTRIES   = 30013
    USE_ALT_URL      = 30014


_ = Language()
