from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    UPDATE_ADDONS     = 30000
    NO_UPDATES        = 30001
    UPDATES_INSTALLED = 30002
    UPDATES_AVAILABLE = 30003
    ATMOS             = 30004
    PROXY_ENABLED     = 30005
    PERSIST_CACHE     = 30006
    WV_LEVEL          = 30007
    WV_LEVEL_AUTO     = 30008
    WV_LEVEL_L1       = 30009
    WV_LEVEL_L3       = 30010

_ = Language()
