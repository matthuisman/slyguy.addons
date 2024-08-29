from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text
from slyguy.constants import *

from .language import _


class Settings(CommonSettings):
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SINGLE_SEASON, default=True)
    HIDE_SUGGESTED = Bool('hide_suggested', _.HIDE_SUGGESTED, default=False)
    HIDE_CLIPS = Bool('hide_clips', _.HIDE_CLIPS, default=False)
    LAT_LONG = Text('lat_long', _.LAT_LONG)


settings = Settings()
