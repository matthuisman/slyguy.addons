import sys
from kodi_six import xbmc

from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Text, Browse

from .language import _


class Settings(CommonSettings):
    SUBTITLES = Bool('subtitles', _.SUBTITLES, default=True)
    AUTO_SUBTITLES = Bool('auto_subtitles', _.AUTO_SUBTITLES, default=True)
    COOKIES_PATH = Browse('cookies_path', _.COOKIES_PATH, type=Browse.FILE)
    PLAY_WITH_NATIVE_APK = Bool('play_with_youtube_apk', _.PLAY_WITH_NATIVE_APK, default=False, visible='system.platform.android')
    NATIVE_APK_ID = Text('android_app_id', _.NATIVE_APK_ID, default_label=_.AUTO, visible='system.platform.android')
    FALLBACK_YOUTUBE_APK = Bool('fallback_youtube_apk', _.FALLBACK_NATIVE_APK, default=False, visible=lambda: sys.version_info[0] > 2 and not Settings.PLAY_WITH_NATIVE_APK.value and xbmc.getCondVisibility('system.platform.android'))


settings = Settings()
