from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    LOGIN_ERROR          = 30003
    STREAM_ERRPR         = 30004
    CATEGORIES           = 30005
    COLLECTIONS          = 30006
    FEATURED             = 30007
    WATCHLIST            = 30008
    WATCHING             = 30009
    SYNC_PLAYBACK        = 30010
    CATEGORY_NOT_FOUND   = 30012
    CHILD_FRIENDLY       = 30013
    ADD_WATCHLIST        = 30015
    REMOVE_WATCHLIST     = 30016
    WATCHLIST_ADDED      = 30017
    WATCHLIST_REMOVED    = 30018


_ = Language()
