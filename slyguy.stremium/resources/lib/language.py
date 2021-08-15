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
    ALL                = 30008
    HIDE_PUBLIC        = 30009
    HIDE_CUSTOM        = 30010
    REMOVE_NUMBERS     = 30011
    SHOW_PROVIDERS     = 30012
    HIDE_MY_CHANNELS   = 30013
    MY_CHANNELS        = 30014
    ADD_MY_CHANNEL     = 30015
    DEL_MY_CHANNEL     = 30016
    MY_CHANNEL_ADDED   = 30017

_ = Language()
