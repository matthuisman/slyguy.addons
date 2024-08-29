from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    RACES                   = 30002
    RACE_NOT_FOUND          = 30003
    NO_STREAMS              = 30004
    SESSION_EXPIRED         = 30005
    SAVE_PASSWORD           = 30006
    SAVE_PASSWORD_RELOGIN   = 30007
    NO_RACES                = 30008
    NOT_PAID                = 30009
    LIVE_LABEL              = 30010


_ = Language()
