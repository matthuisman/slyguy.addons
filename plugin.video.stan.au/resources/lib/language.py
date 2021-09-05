from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LOGIN_ERROR           = 30003
    GEO_ERROR             = 30005
    ENABLE_H265           = 30008
    TV                    = 30009
    MOVIES                = 30010
    KIDS                  = 30011
    FEATURED              = 30012
    ENABLE_4K             = 30013

    PLAYBACK_ERROR        = 30015
    TRAILERS_EXTRAS       = 30016

    SELECT_PROFILE        = 30019
    PROFILE_ACTIVATED     = 30020

    KID_LOCKDOWN          = 30031

    KIDS_PLAY_DENIED      = 30033
    MY_LIST               = 30034
    CONTINUE_WATCHING     = 30035
    GOTO_SERIES           = 30036
    SPORT                 = 30037
    HIDE_SPORT            = 30038

_ = Language()
