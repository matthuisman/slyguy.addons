from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LOGIN_ERROR           = 30003
    GEO_ERROR             = 30005
    FEATURED              = 30012

    PLAYBACK_ERROR        = 30015
    TRAILERS_EXTRAS       = 30016

    SELECT_PROFILE        = 30019
    PROFILE_ACTIVATED     = 30020

    KIDS_PLAY_DENIED      = 30033
    MY_LIST               = 30034
    CONTINUE_WATCHING     = 30035
    GOTO_SERIES           = 30036

_ = Language()
