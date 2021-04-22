from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME     = 30001
    ASK_PASSWORD     = 30002
    LOGIN_ERROR      = 30003
    CHANNELS         = 30004
    FEATURED         = 30005
    NO_DATA          = 30006
    WHATS_ON         = 30007
    SPORTS           = 30008
    LIVE             = 30009
    DATE_FORMAT      = 30010
    NO_ASSET_ERROR   = 30011
    NO_MPD_ERROR     = 30012
    NO_ENTITLEMENT   = 30013
    TOKEN_ERROR      = 30014

    SET_REMINDER     = 30020
    REMOVE_REMINDER  = 30021
    FREEMIUM         = 30022
    REMINDER_SET     = 30023
    REMINDER_REMOVED = 30024
    EVENT_STARTED    = 30025
    WATCH            = 30026
    CLOSE            = 30027

_ = Language()