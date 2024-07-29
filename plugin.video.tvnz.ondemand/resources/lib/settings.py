from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


class Settings(CommonSettings):
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SEASONS, default=True)
    HIDE_EMPTY_SHOWS = Bool('hide_empty_shows', _.HIDE_EMPTY_SHOWS, default=True)


settings = Settings()
