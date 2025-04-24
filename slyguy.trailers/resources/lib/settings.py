from slyguy.util import set_kodi_string
from slyguy.constants import IS_ANDROID
from slyguy.settings import CommonSettings, is_donor
from slyguy.settings.types import Bool, Browse, Text

from .language import _


def set_trailer_context():
    if not settings.TRAILER_CONTEXT_MENU.value:
        # dont show
        set_kodi_string('_slyguy_trailer_context_menu', '0')
    elif settings.TRAILER_LOCAL.value:
        # always show
        set_kodi_string('_slyguy_trailer_context_menu', '4')
    elif settings.MDBLIST.value:
        # show if unique id to find via mdblist
        set_kodi_string('_slyguy_trailer_context_menu', '2')
        if settings.MDBLIST_SEARCH.value:
            # no unique id, but search enabled so show if name/year
            set_kodi_string('_slyguy_trailer_context_menu', '3')
    else:
        # show if trailer path on listitem
        set_kodi_string('_slyguy_trailer_context_menu', '1')


class Settings(CommonSettings):
    TRAILER_CONTEXT_MENU = Bool('trailer_context_menu', _.TRAILER_CONTEXT_MENU, default=True, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, disabled_value=False, enable=is_donor, disabled_reason=_.SUPPORTER_ONLY)
    TRAILER_LOCAL = Bool('trailer_local', _.TRAILER_LOCAL, default=False, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=TRAILER_CONTEXT_MENU)

    MDBLIST = Bool('mdblist', _.MDBLIST, default=False, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=TRAILER_CONTEXT_MENU)
    MDBLIST_SEARCH = Bool('mdblist_search', _.MDBLIST_SEARCH, default=True, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=MDBLIST)

    YT_APK = Bool('yt_apk', _.YT_APK, default=False, visible=IS_ANDROID)
    YT_APK_ID = Text('yt_apk_id', _.YT_NATIVE_APK_ID, default_label=_.AUTO, parent=YT_APK)

    YT_DLP = Bool('yt_dlp', _.YT_DLP, default=True, disabled_value=False)
    YT_SUBTITLES = Bool('dlp_subtitles', _.YT_SUBTITLES, default=True, parent=YT_DLP)
    YT_AUTO_SUBTITLES = Bool('dlp_auto_subtitles', _.YT_AUTO_SUBTITLES, default=True, parent=YT_DLP)
    YT_COOKIES_PATH = Browse('dlp_cookies_path', _.YT_DLP_COOKIES_PATH, type=Browse.FILE, parent=YT_DLP)


settings = Settings()
