from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME          = 30000
    ASK_PASSWORD          = 30001
    TV                    = 30002
    MOVIES                = 30003
    SEASON                = 30004
    LOGIN_ERROR           = 30005
    KIDS                  = 30006
    KID_LOCKDOWN          = 30007
    PROFILE_SET_ERROR     = 30008

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

_ = Language()