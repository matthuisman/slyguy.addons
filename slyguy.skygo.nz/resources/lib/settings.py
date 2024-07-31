from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool

from .language import _


HEADERS = {
    'User-Agent': 'okhttp/4.9.3',
}

CLIENT_ID = 'kOBPdd3dPUvJJz96QdaJdrqZZD7kWmI4'
GRAPH_URL = 'https://api.skyone.co.nz/exp/graph'
EPG_URL = 'https://i.mjh.nz/SkyGo/epg.xml.gz'


class Settings(CommonSettings):
    SUBSCRIBED_ONLY = Bool('subscribed_only', _.SUBSCRIBED_ONLY, default=True)
    FLATTEN_SINGLE_SEASON = Bool('flatten_single_season', _.FLATTEN_SEASONS, default=True)


settings = Settings()
