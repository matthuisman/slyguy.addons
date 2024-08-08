from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


class Settings(CommonSettings):
    SAVE_PASSWORD = Bool('save_password', _.SAVE_PASSWORD, default=False)


settings = Settings()
