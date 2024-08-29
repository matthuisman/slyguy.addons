from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text

from .language import _


class Settings(CommonSettings):
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SEASONS, default=True)
    DEVICE_ID = Text('device_id', _.DEVICE_ID, default='{mac_address}')


settings = Settings()
