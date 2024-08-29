from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    FUNCTION      = 30000
    SILENT        = 30001
    RUN_FUNCTION  = 30002


_ = Language()
