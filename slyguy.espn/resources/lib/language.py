from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LIVE               = 30000
    LOGIN_STEPS        = 30001
    NOT_ENTITLED       = 30002
    GEO_ERROR          = 30003
    API_ERROR          = 30004
    ESPN_LOGIN         = 30005
    ESPN_LOGOUT        = 30006
    PROVIDER_LOGIN     = 30007
    PROVIDER_LOOUT     = 30008
    ACCOUNT            = 30009
    NO_SOURCE          = 30010

_ = Language()
