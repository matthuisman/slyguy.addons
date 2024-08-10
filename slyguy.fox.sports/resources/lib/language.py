from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    LOGIN_STEPS          = 30000
    PROVIDER_LOGIN       = 30001
    LIVE                 = 30002
    NO_STREAM_ID         = 30005
    NO_VIDEO_FOUND       = 30006
    ERROR_REFRESH_TOKEN  = 30007
    HIDE_UNENTITLED      = 30008


_ = Language()
