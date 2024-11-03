from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


DATA_URL = 'https://i.mjh.nz/PlutoTV/.app.json.gz'
ALL = 'all'
MY_CHANNELS = 'my_channels'
UUID_NAMESPACE = '122e1611-0232-4336-bf43-e054c8ecd0d5'


class Settings(CommonSettings):
    USE_URL_ALT = Bool('use_url_alt', _.USE_ALT_URL, default=False)
    SHOW_COUNTRIES = Bool('show_countries', _.SHOW_COUNTRIES, default=True)
    SHOW_GROUPS = Bool('show_groups', _.SHOW_GROUPS, default=True)
    SHOW_CHNOS = Bool('show_chnos', default=True)
    SHOW_EPG = Bool('show_epg', default=True)


settings = Settings()
