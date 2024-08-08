from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    LOGIN_ERROR          = 30003
    WATCHLIST            = 30004
    FAVOURITES           = 30005
    ALL_SHOWS            = 30006
    POPULAR              = 30007
    NEW_SHOWS            = 30008
    DEVOTIONALS          = 30009
    ADD_WATCHLIST        = 30010
    REMOVE_WATCHLIST     = 30011
    ADD_FAVOURITE        = 30012
    REMOVE_FAVOURITE     = 30013
    SESSION_EXPIRED      = 30014
    SESSION_EXPIRED_DESC = 30015
    SAVE_PASSWORD        = 30016
    FAVOURITE_ADDED      = 30017
    WATCHLIST_ADDED      = 30018


_ = Language()
