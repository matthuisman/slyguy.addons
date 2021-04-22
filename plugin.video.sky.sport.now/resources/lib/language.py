from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME     = 30001
    ASK_PASSWORD     = 30002
    LIVE_TV          = 30003
    HIGHLIGHTS       = 30004
    PAGE_TITLE       = 30005
    NEXT_PAGE        = 30006
    GEO_ERROR        = 30007
    PLAYBACK_ERROR   = 30008
    UNKNOWN_ERROR    = 30009
    LOGIN_ERROR      = 30010
    REPLAY           = 30011
    NOT_STARTED_YET  = 30012
    EVENT_EXPIRED    = 30013

_ = Language()