from slyguy.settings import CommonSettings
from slyguy.settings.types import Number

from .language import _


class Settings(CommonSettings):
    POLL_TIME = Number('poll_time', _.POLL_TIME, default=10, lower_limit=10, upper_limit=300)


settings = Settings()
