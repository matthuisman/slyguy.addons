from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME           = 30000
    ASK_PASSWORD           = 30001
    TOKEN_ERROR            = 30002
    REFRESH_TOKEN_ERROR    = 30003
    LOGIN_ERROR            = 30004
    LIVE_TV                = 30005

_ = Language()
