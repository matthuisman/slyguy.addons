from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text

from .language import _


class Settings(CommonSettings):
    LAT_LONG = Text('lat_long', _.LAT_LONG, default_label=_.AUTO)
    SYNC_PLAYBACK = Bool('sync_playback', _.SYNC_PLAYBACK, default=False)
    DEVICE_ID = Text('device_id', _.DEVICE_ID, default='{mac_address}')

    HIDE_LOCKED = Bool('hide_locked', _.HIDE_LOCKED, default=True)
    HIDE_MY_STUFF = Bool('hide_my_stuff', _.HIDE_MY_STUFF, default=False)
    HIDE_UPCOMING = Bool('hide_upcoming', _.HIDE_UPCOMING, default=False)
    HIDE_KIDS = Bool('hide_kids', _.HIDE_KIDS, default=False)
    HIDE_LIVE_CHANNELS = Bool('hide_live_channels', _.HIDE_LIVE_CHANNELS, default=False)
    SECONDARY_AUDIO = Bool('secondary_audio', _.SECONDARY_AUDIO, default=False)


settings = Settings()
