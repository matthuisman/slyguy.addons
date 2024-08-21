from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    HISTORY_LENGTH      = 30000
    SMART_SEARCH        = 30001
    SEARCH_TITLE        = 30002
    SEARCH_ORIG_TITLE   = 30003
    SEARCH_TAGS         = 30004
    CLEAR_HISTORY       = 30005
    HISTORY_CLEARED     = 30006

    SEARCH_MOVIES       = 32001
    SEARCH_TV_SHOWS     = 32002
    SEARCH_EPISODES     = 32003
    SEARCH_ACTORS       = 32011
    SEARCH_DIRECTORS    = 32012
    SEARCH_TV_ACTORS    = 32013
    SEARCH_MUSIC_VIDEOS = 32004
    SEARCH_LIVE_TV      = 32009
    SEARCH_ARTISTS      = 32005
    SEARCH_ALBUMS       = 32006
    SEARCH_SONGS        = 32007


_ = Language()
