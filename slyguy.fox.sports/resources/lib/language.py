from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LOGIN_STEPS          = 30000
    PROVIDER_LOGIN       = 30001
    LIVE                 = 30002
    ENABLE_4K            = 30003
    ENABLE_HDR           = 30004
    NO_STREAM_ID         = 30005
    NO_VIDEO_FOUND       = 30006
    ERROR_REFRESH_TOKEN  = 30007

_ = Language()
