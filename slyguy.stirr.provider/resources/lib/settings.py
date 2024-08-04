from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


DATA_URL = 'https://i.mjh.nz/Stirr/app.json.gz'
EPG_URL = 'https://i.mjh.nz/Stirr/all.xml.gz'
ALL = 'all'
MY_CHANNELS = 'my_channels'


class Settings(CommonSettings):
    SHOW_GROUPS = Bool('show_groups', _.SHOW_GROUPS, default=True)
    SHOW_CHNOS = Bool('show_chnos', default=True)
    SHOW_EPG = Bool('show_epg', default=True)


settings = Settings()
