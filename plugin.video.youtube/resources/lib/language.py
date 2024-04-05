from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    PLAY_WITH_NATIVE_APK = 30001
    FALLBACK_NATIVE_APK = 30002
    NATIVE_APK_ID = 30003
    PYTHON3_NOT_SUPPORTED = 30004
    PYTHON3_NOT_SUPPORTED_ANDROID = 30005
    NO_VIDEOS_FOUND = 30006


_ = Language()
