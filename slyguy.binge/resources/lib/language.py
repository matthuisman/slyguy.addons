from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME          = 30001
    ASK_PASSWORD          = 30002
    LOGIN_ERROR           = 30003
    ADD_PROFILE           = 30004
    SELECT_PROFILE        = 30005
    DELETE_PROFILE        = 30006
    PROFILE_ACTIVATED     = 30007
    RANDOM_AVATAR         = 30008
    SELECT_AVATAR         = 30009
    AVATAR_USED           = 30010
    AVATAR_NOT_USED       = 30011
    PROFILE_NAME          = 30012
    PROFILE_NAME_TAKEN    = 30013
    SELECT_DELETE_PROFILE = 30014
    DELTE_PROFILE_HEADER  = 30015
    DELETE_PROFILE_INFO   = 30016
    PROFILE_DELETED       = 30017
    FEATURED              = 30018
    SHOWS                 = 30019
    MOVIES                = 30020
    BINGE_LISTS           = 30021
    LIVE_CHANNELS         = 30022
    ASSET_ERROR           = 30023
    HEVC                  = 30024
    LOGIN_WITH            = 30025
    DEVICE_LINK           = 30026
    EMAIL_PASSWORD        = 30027
    DEVICE_LINK_STEPS     = 30028
    WV_SECURE             = 30029
    REFRESH_TOKEN_ERROR   = 30030
    SHOW_HERO_CONTENTS    = 30031
    TOKEN_ERROR           = 30032

_ = Language()