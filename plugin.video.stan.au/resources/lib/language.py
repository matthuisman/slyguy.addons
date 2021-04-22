from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME          = 30001
    ASK_PASSWORD          = 30002
    LOGIN_ERROR           = 30003

    IP_ADDRESS_ERROR      = 30005

    TV                    = 30009
    MOVIES                = 30010
    KIDS                  = 30011
    FEATURED              = 30012
    SEARCH_FOR            = 30013
    NEXT_PAGE             = 30014
    PLAYBACK_ERROR        = 30015
    TRAILERS_EXTRAS       = 30016
    ADD_PROFILE           = 30017
    DELETE_PROFILE        = 30018
    SELECT_PROFILE        = 30019
    PROFILE_ACTIVATED     = 30020
    SELECT_DELETE_PROFILE = 30021
    DELETE_PROFILE_INFO   = 30022
    DELTE_PROFILE_HEADER  = 30023
    PROFILE_DELETED       = 30024
    RANDOM_AVATAR         = 30025
    AVATAR_USED           = 30026
    SELECT_AVATAR         = 30027
    PROFILE_NAME          = 30028
    KIDS_PROFILE          = 30029
    KIDS_PROFILE_INFO     = 30030
    KID_LOCKDOWN          = 30031
    PROFILE_NAME_TAKEN    = 30032
    KIDS_PLAY_DENIED      = 30033
    MY_LIST               = 30034
    CONTINUE_WATCHING     = 30035
    GOTO_SERIES           = 30036
    SPORT                 = 30037
    HIDE_SPORT            = 30038

_ = Language()