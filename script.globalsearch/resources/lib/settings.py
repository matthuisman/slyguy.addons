from slyguy import gui
from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Number, List, Action

from .language import _


def clear_history():
    settings.HISTORY.clear()
    gui.notification(_.HISTORY_CLEARED)


class Settings(CommonSettings):
    CLEAR_HISTORY = Action(clear_history, _.CLEAR_HISTORY, confirm_action=True)
    HISTORY_LENGTH = Number('history_length', _.HISTORY_LENGTH, default=20, lower_limit=0, upper_limit=100)
    SMART_SEARCH = Bool('smart_search', _.SMART_SEARCH, default=True)
    SEARCH_TITLE = Bool('search_title', _.SEARCH_TITLE, default=True)
    SEARCH_ORIG_TITLE = Bool('search_originaltitle', _.SEARCH_ORIG_TITLE, default=True)
    SEARCH_TAGS = Bool('search_tags', _.SEARCH_TAGS, default=False)

    SEARCH_MOVIES = Bool('movies', _.SEARCH_MOVIES, default=True)
    SEARCH_TV_SHOWS = Bool('tvshows', _.SEARCH_TV_SHOWS, default=True)
    SEARCH_EPISODES = Bool('episodes', _.SEARCH_EPISODES, default=False)
    SEARCH_ACTORS = Bool('actors', _.SEARCH_ACTORS, default=False)
    SEARCH_DIRECTORS = Bool('directors', _.SEARCH_DIRECTORS, default=False)
    SEARCH_TV_ACTORS = Bool('tvactors', _.SEARCH_TV_ACTORS, default=False)
    SEARCH_MUSIC_VIDEOS = Bool('musicvideos', _.SEARCH_MUSIC_VIDEOS, default=False)
    SEARCH_LIVE_TV = Bool('livetv', _.SEARCH_LIVE_TV, default=False)
    SEARCH_ARTISTS = Bool('artists', _.SEARCH_ARTISTS, default=False)
    SEARCH_ALBUMS = Bool('albums', _.SEARCH_ALBUMS, default=False)
    SEARCH_SONGS = Bool('songs', _.SEARCH_SONGS, default=False)

    HISTORY = List('searches', visible=False)
    VIEW = Number('view', default=50, visible=False)


settings = Settings()
