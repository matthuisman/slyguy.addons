from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text, Action

from .language import _


class Settings(CommonSettings):
    DEVICE_ID = Text('device_id', _.DEVICE_ID, default='kodi{mac_address}{system}{arch}')
    SKIP_INTROS = Bool('skip_intros', _.SKIP_INTROS, default=False)
    SKIP_CREDITS = Bool('skip_credits', _.SKIP_CREDITS, default=True)
    PLAY_NEXT_EPISODE = Bool('play_next_episode', _.PLAY_NEXT_EPISODE, default=True)
    PLAY_NEXT_MOVIE = Bool('play_next_movie', _.PLAY_NEXT_MOVIE, default=False)
    SYNC_WATCHLIST = Bool('sync_watchlist', _.SYNC_WATCHLIST, default=True)
    SYNC_PLAYBACK = Bool('sync_playback', _.SYNC_PLAYBACK, default=False)
    SELECT_LANGUAGE = Action('RunPlugin(plugin://$ID/?_=select_language)', _.SELECT_LANGUAGE)
    PLAYBACK_LANGUAGE = Text('playback_language', _.PLAYBACK_LANGUAGE, default='en')


settings = Settings()
