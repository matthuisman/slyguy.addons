from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


class Settings(CommonSettings):
    SHOW_NO_URL_STATIONS = Bool('show_no_streams', _.SHOW_NO_URL_STATIONS, default=False)
    SHOW_EPG = Bool('show_epg', default=True)


settings = Settings()
