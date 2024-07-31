from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    DEVICE_ID        = 30000
    KIDS_PROFILE     = 30001
    ENTER_PIN        = 30002
    LAT_LONG         = 30004
    SECONDARY_AUDIO  = 30009
    SYNC_PLAYBACK    = 30010
    MY_STUFF         = 30011
    HIDE_MY_STUFF    = 30012
    KEEP_WATCHING    = 30013
    REMOVE_MY_STUFF  = 30014
    ADD_MY_STUFF     = 30015
    ADDED_MY_STUFF   = 30016
    COMING_SOON      = 30017
    HOME             = 30018
    TV               = 30019
    SPORTS           = 30021
    HUBS             = 30022
    HIDE_LOCKED      = 30023
    LOCKED           = 30024
    EXPIRED_TOKEN    = 30025
    HIDE_UPCOMING    = 30026
    UPCOMING         = 30027
    NO_LISTINGS      = 30028
    NO_ENTITY        = 30029
    NO_DEVICE_CODE   = 30030
    PROFILE_ERROR    = 30031
    KIDS             = 30033
    HIDE_KIDS        = 30034
    HIDE_LIVE_CHANNELS = 30035
    LIVE             = 30038


_ = Language()
