from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME     = 30001
    ASK_PASSWORD     = 30002
    LOGIN_ERROR      = 30003
    PLAYBACK_ERROR   = 30004
    LIVE             = 30005
    PLAYED           = 30006
    UPCOMING         = 30007
    SHOW_SCORES      = 30008
    NO_MATCHES       = 30009
    REMINDER_SET     = 30010
    REMINDER_REMOVED = 30011
    UPCOMING_MATCH   = 30012
    DATE_FORMAT      = 30013
    MATCH_PLOT       = 30014
    MATCH_STARTED    = 30015
    MULTIPART_VIDEO  = 30016
    PLAYBACK_SOURCE  = 30017
    WATCH            = 30018
    CLOSE            = 30019
    SUBSCRIBE_ERROR  = 30020
    NO_VIDEOS        = 30021

_ = Language()