from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LOGIN_ERROR           = 30001
    REFRESH_TOKEN_ERROR   = 30002
    TOKEN_ERROR           = 30003

_ = Language()
