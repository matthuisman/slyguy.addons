from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    PROFILE_WITH_PIN      = 30000
    PROFILE_KIDS          = 30001
    ENTER_PIN             = 30002
    API_ERROR             = 30003
    INVALID_TOKEN         = 30004
    LOGIN_ERROR           = 30005
    PROVIDER_LOGIN        = 30006
    HOME                  = 30007
    SERIES                = 30008
    MOVIES                = 30009
    GOTO_SERIES           = 30010

_ = Language()
