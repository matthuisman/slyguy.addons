from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LOGIN_ERROR        = 30003
    DEREGISTER_CHOOSE  = 30004
    LIVE_TV            = 30005
    PLAYBACK_ERROR     = 30006
    NO_STREAM_ERROR    = 30007
    SAVE_PASSWORD      = 30008
    WIDEVINE_LEVEL     = 30009
    TV_SHOWS           = 30010
    TOKEN_ERROR        = 30011
    SPORTS             = 30012
    MOVIES             = 30013
    SEASON             = 30014
    EPISODE_MENU_TITLE = 30015
    GO_TO_SHOW_CONTEXT = 30016
    KIDS               = 30017
    HIDE_LOCKED        = 30018
    CHANNEL            = 30019
    LOCKED             = 30020
    DEVICE_NAME        = 30021
    DEVICE_ID          = 30022
    RECOMMENDED        = 30023
    EPISODE_SUBTITLE   = 30024
    SEARCH             = 30025
    SEARCH_FOR         = 30026
    CONTINUE_WATCHING  = 30027
    WATCHLIST          = 30028
    SHOW_EPG           = 30029

_ = Language()
