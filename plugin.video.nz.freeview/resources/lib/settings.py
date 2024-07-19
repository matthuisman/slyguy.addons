from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *

from .language import _


DATA_URL = 'https://i.mjh.nz/nz/tv.json.gz'
EPG_URL = 'https://i.mjh.nz/nz/epg.xml.gz'


class ChannelMode:
    ALL = 'ALL'
    FREEVIEW_ONLY = 'FREEVIEW_ONLY'
    FAST_ONLY = 'FAST_ONLY'


class Settings(CommonSettings):
    SHOW_EPG = Bool('show_epg', _.SHOW_EPG, default=True)
    SHOW_CHNOS = Bool('show_chnos', _.SHOW_CHNOS, default=True)
    CHANNEL_MODE = Enum('channel_mode', _.CHANNEL_MODE, default=ChannelMode.ALL, loop=True,
                    options=[[_.ALL, ChannelMode.ALL], [_.FREEVIEW_ONLY, ChannelMode.FREEVIEW_ONLY], [_.FAST_ONLY, ChannelMode.FAST_ONLY]])


settings = Settings()
