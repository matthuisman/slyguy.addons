from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME       = 30001
    ASK_PASSWORD       = 30002
    LOGIN_ERROR        = 30003
    CHANNELS           = 30004
    FEATURED           = 30005
    GEO_BLOCKED        = 30006
    NO_STREAM          = 30007
    LIVE               = 30008
    DATE_FORMAT        = 30009
    REMINDER_SET       = 30010
    REMINDER_REMOVED   = 30011
    EVENT_STARTED      = 30012
    WATCH              = 30013
    CLOSE              = 30014

_ = Language()