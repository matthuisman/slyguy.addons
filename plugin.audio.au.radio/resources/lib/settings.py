from slyguy.settings import CommonSettings
from slyguy.settings.types import Enum
from slyguy.constants import *

from .language import _


DATA_URL = 'https://i.mjh.nz/au/{region}/radio.json.gz'


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


class Settings(CommonSettings):
    REGION = Enum('region_index', _.REGION, default=Region.SYDNEY,
                    options=[[_.SYDNEY, Region.SYDNEY], [_.MELBOURNE, Region.MELBOURNE], [_.BRISBANE, Region.BRISBANE], [_.PERTH, Region.PERTH],
                        [_.ADELAIDE, Region.ADELAIDE], [_.DARWIN, Region.DARWIN], [_.HOBART, Region.HOBART], [_.CANBERRA, Region.CANBERRA], [_.ALL, Region.ALL]])


settings = Settings()
