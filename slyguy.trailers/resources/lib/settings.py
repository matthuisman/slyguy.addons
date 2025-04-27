from slyguy import plugin
from slyguy.util import set_kodi_string
from slyguy.constants import IS_ANDROID, IS_PYTHON3
from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Browse, Text, Enum, Action

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


class YTMode:
    YOUTUBE_PLUGIN = 'youtube_plugin'
    TUBED_PLUGIN = 'tubed_plugin'
    APK = 'apk'
    YT_DLP = 'yt-dlp'


YT_OPTIONS = []
if IS_PYTHON3:
    YT_OPTIONS.append([_.YT_DLP, YTMode.YT_DLP])
if IS_ANDROID:
    YT_OPTIONS.append([_.YT_APK, YTMode.APK])
YT_OPTIONS.append([_.YOUTUBE_PLUGIN, YTMode.YOUTUBE_PLUGIN])
YT_OPTIONS.append([_.TUBED_PLUGIN, YTMode.TUBED_PLUGIN])


class Settings(CommonSettings):
    TRAILER_CONTEXT_MENU = Bool('trailer_context_menu', _.TRAILER_CONTEXT_MENU, default=True, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context)
    TRAILER_LOCAL = Bool('trailer_local', _.TRAILER_LOCAL, default=False, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=TRAILER_CONTEXT_MENU)
    MDBLIST = Bool('mdblist', _.MDBLIST, default=False, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=TRAILER_CONTEXT_MENU)
    MDBLIST_SEARCH = Bool('mdblist_search', _.MDBLIST_SEARCH, default=True, after_save=lambda val:set_trailer_context(), after_clear=set_trailer_context, parent=MDBLIST)

    YT_PLAY_WITH = Enum('yt_play_with', _.YT_PLAY_WITH, options=YT_OPTIONS, default=YT_OPTIONS[0][1])

    YT_SUBTITLES = Bool('dlp_subtitles', _.YT_SUBTITLES, default=True, visible=lambda: settings.YT_PLAY_WITH.value == YTMode.YT_DLP, parent=YT_PLAY_WITH)
    YT_AUTO_SUBTITLES = Bool('dlp_auto_subtitles', _.YT_AUTO_SUBTITLES, default=True, visible=lambda: settings.YT_PLAY_WITH.value == YTMode.YT_DLP, parent=YT_PLAY_WITH)
    YT_COOKIES_PATH = Browse('dlp_cookies_path', _.YT_DLP_COOKIES_PATH, type=Browse.FILE, visible=lambda: settings.YT_PLAY_WITH.value == YTMode.YT_DLP, parent=YT_PLAY_WITH)
    YT_PLAY_FALLBACK = Enum('yt_play_fallback', _.YT_PLAY_FALLBACK, options=[x for x in YT_OPTIONS if x[1] != YTMode.YT_DLP], visible=lambda: settings.YT_PLAY_WITH.value == YTMode.YT_DLP, parent=YT_PLAY_WITH)

    YT_APK_ID = Text('yt_apk_id', _.YT_NATIVE_APK_ID, default_label=_.AUTO, visible=lambda: settings.YT_PLAY_WITH.value == YTMode.APK or settings.YT_PLAY_FALLBACK.value == YTMode.APK, parent=YT_PLAY_WITH)

    TESTSTREAMS = Action("Container.Update({})".format(plugin.url_for('/test_streams')), _.TEST_STREAMS)


settings = Settings()
