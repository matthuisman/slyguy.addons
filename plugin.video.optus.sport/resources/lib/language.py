from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    LOGIN_ERROR        = 30003
    FEATURED           = 30005
    GEO_BLOCKED        = 30006
    NO_STREAM          = 30007
    LIVE               = 30008
    DATE_FORMAT        = 30009


_ = Language()
