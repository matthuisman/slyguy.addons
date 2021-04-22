from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME      = 30001
    ASK_PASSWORD      = 30002
    DEVICE_LINK       = 30003
    EMAIL_PASSWORD    = 30004
    DEVICE_LINK_STEPS = 30005
    LOGIN_WITH        = 30006
    NO_STREAM         = 30007
    LIVE_CHANNELS     = 30008
    CATCH_UP          = 30009
    
_ = Language()