from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool


class Settings(CommonSettings):
    ENABLE_CHAPTERS = Bool('enable_chapters', default=False)


settings = Settings()
