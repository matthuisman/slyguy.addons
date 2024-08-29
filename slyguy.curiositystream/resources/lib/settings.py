from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool
from slyguy.constants import *

from .language import _


class Settings(CommonSettings):
    CHILD_FRIENDLY = Bool('child_friendly', _.CHILD_FRIENDLY, default=False)
    SYNC_PLAYBACL = Bool('sync_playback', _.SYNC_PLAYBACK, default=False)


settings = Settings()
