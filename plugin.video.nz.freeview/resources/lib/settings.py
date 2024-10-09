from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *
from slyguy.language import _


DATA_URL = 'https://i.mjh.nz/nz/tv.json.gz'


class ChannelMode:
    ALL = 'ALL'
    OTA_ONLY = 'OTA_ONLY'
    FAST_ONLY = 'FAST_ONLY'


class Settings(CommonSettings):
    SHOW_EPG = Bool('show_epg', default=True)
    SHOW_CHNOS = Bool('show_chnos', default=True)
    CHANNEL_MODE = Enum('channel_mode', default=ChannelMode.ALL, loop=True,
                    options=[[_.ALL, ChannelMode.ALL], [_.OTA_ONLY, ChannelMode.OTA_ONLY], [_.FAST_ONLY, ChannelMode.FAST_ONLY]])


settings = Settings()
