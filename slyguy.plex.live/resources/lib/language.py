from slyguy.language import BaseLanguage
from .constants import *

class Language(BaseLanguage):
    LIVE_TV          = 30000
    SHOW_CH_NO       = 30001
    REGION           = 30002
    ALL              = 30003
    SHOW_EPG         = 30004
    SELECT_REGIONS   = 30005
    CHANNEL_COUNT    = 30006
    NO_REGIONS       = 30007
    MY_CHANNELS      = 30008
    ADD_MY_CHANNEL   = 30009
    DEL_MY_CHANNEL   = 30010
    MY_CHANNEL_ADDED = 30011
    SHOW_GROUPS      = 30012
    SHOW_COUNTRIES   = 30013

_ = Language()
