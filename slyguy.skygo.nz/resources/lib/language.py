from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    TOKEN_ERROR            = 30002
    REFRESH_TOKEN_ERROR    = 30003
    LOGIN_ERROR            = 30004
    CONCURRENT_STREAMS     = 30006
    SUBSCRIPTION_REQUIRED  = 30007
    COMING_SOON            = 30009
    FLATTEN_SEASONS        = 30011
    FEATURED               = 30012
    API_ACCESS_DENIED      = 30013
    SUBSCRIBED_ONLY        = 30014


_ = Language()
