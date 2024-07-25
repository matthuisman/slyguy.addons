from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Enum
from slyguy.constants import *

from .language import _


DATA_URL = 'https://i.mjh.nz/au/{region}/tv.json.gz'
EPG_URL = 'https://i.mjh.nz/au/{region}/epg.xml.gz'


class Region:
    SYDNEY = 'Sydney'
    MELBOURNE = 'Melbourne'
    BRISBANE = 'Brisbane'
    PERTH = 'Perth'
    ADELAIDE = 'Adelaide'
    DARWIN = 'Darwin'
    HOBART = 'Hobart'
    CANBERRA = 'Canberra'
    ALL = 'all'


class ChannelMode:
    ALL = 'ALL'
    OTA_ONLY = 'OTA_ONLY'
    FAST_ONLY = 'FAST_ONLY'


class Settings(CommonSettings):
    REGION = Enum('region_index', _.REGION, default=Region.SYDNEY,
                    options=[[_.SYDNEY, Region.SYDNEY], [_.MELBOURNE, Region.MELBOURNE], [_.BRISBANE, Region.BRISBANE], [_.PERTH, Region.PERTH],
                        [_.ADELAIDE, Region.ADELAIDE], [_.DARWIN, Region.DARWIN], [_.HOBART, Region.HOBART], [_.CANBERRA, Region.CANBERRA], [_.ALL, Region.ALL]])
    SHOW_EPG = Bool('show_epg', default=True)
    SHOW_CHNOS = Bool('show_chnos', default=True)
    CHANNEL_MODE = Enum('channel_mode', default=ChannelMode.ALL, loop=True,
                    options=[[_.ALL, ChannelMode.ALL], [_.OTA_ONLY, ChannelMode.OTA_ONLY], [_.FAST_ONLY, ChannelMode.FAST_ONLY]])


settings = Settings()
