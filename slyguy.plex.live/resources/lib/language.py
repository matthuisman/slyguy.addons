from slyguy.language import BaseLanguage
from .constants import *

class Language(BaseLanguage):
    LIVE_TV        = 30000
    NO_VIDEO_FOUND = 30001
    REGION         = 30002
    ALL            = 30003
    SHOW_EPG       = 30004
    SELECT_REGIONS = 30005
    CHANNEL_COUNT  = 30006
    NO_REGIONS     = 30007

_ = Language()
