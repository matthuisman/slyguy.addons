from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool


class Settings(CommonSettings):
    SHOW_EPG = Bool('show_epg', default=True)


settings = Settings()
