from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME       = 30000
    ASK_PASSWORD       = 30001
    REGISTER           = 30002
    CONFIRM_PASSWORD   = 30003
    PASSWORD_NOT_MATCH = 30004
    LIVE_TV            = 30005
    SELECT_PROVIDERS   = 30006
    NO_PROVIDERS       = 30007

_ = Language()
