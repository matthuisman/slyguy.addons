from slyguy.language import BaseLanguage
from .constants import *

class Language(BaseLanguage):
    LIVE_TV        = 30000
    SHOW_CH_NO     = 30001
    REGION         = 30002
    ALL            = 30003
    SHOW_EPG       = 30004
    MERGE_ADDED    = 30005
    MERGE_REMOVED  = 30006
    MERGE_INCLUDED = 30007
    CHANNEL_COUNT  = 30008
    MERGE_ADD      = 30009
    MERGE_REMOVE   = 30010

_ = Language()
