from kodi_six import xbmcgui

from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text

from .language import _


class Settings(CommonSettings):
    SYNC_PLAYBACK = Bool('sync_playback', _.SYNC_PLAYBACK, default=False)
    REGION_IP = Text('region_ip', _.REGION_IP, default_label=_.AUTO, input_type=xbmcgui.INPUT_IPADDRESS)
    DEVICE_ID = Text('device_id', _.DEVICE_ID, default='{mac_address}')


settings = Settings()
