from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    DEVICE_ID             = 30003
    API_ERROR             = 30004
    GO_TO_SERIES          = 30005
    NO_VIDEO_FOUND        = 30006
    PLAYBACK_LANGUAGE     = 30009
    PLAY_NEXT_EPISODE     = 30010
    SKIP_INTROS           = 30011
    PLAY_NEXT_MOVIE       = 30012
    SKIP_CREDITS          = 30013
    FEATURED              = 30019
    ORIGINALS             = 30022
    JUST_ADDED            = 30023
    LAST_CHANCE           = 30024
    COMING_SOON           = 30025
    TRENDING_NOW          = 30026
    BLOCKED_IP            = 30027
    GEO_LOCKED            = 30028
    FULL_DETAILS          = 30029
    EXTRAS                = 30030
    SYNC_WATCHLIST        = 30032
    SYNC_PLAYBACK         = 30033
    WATCHLIST             = 30034
    CONTINUE_WATCHING     = 30035
    ADDED_WATCHLIST       = 30036
    ADD_WATCHLIST         = 30037
    REMOVE_WATCHLIST      = 30038
    PLAYBACK_LANGUAGE     = 30039
    SELECT_LANGUAGE       = 304


_ = Language()
