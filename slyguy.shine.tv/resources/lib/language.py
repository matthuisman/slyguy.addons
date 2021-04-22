from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME      = 30001
    ASK_PASSWORD      = 30002
    LOGIN_FAILED      = 30003
    LOGIN_FORM_ERROR  = 30004
    DEVICE_LIMIT      = 30005
    FEATURED          = 30006
    BROWSE            = 30007

    LIVE              = 30009
    LIVE_NOW          = 30010

_ = Language()