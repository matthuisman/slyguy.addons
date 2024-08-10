from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


class Settings(CommonSettings):
    HIDE_UNENTITLED = Bool('hide_unentitled', _.HIDE_UNENTITLED, default=True)


settings = Settings()
