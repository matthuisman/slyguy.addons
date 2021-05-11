from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    MY_COURSES       = 30001
    ASK_USERNAME     = 30004
    ASK_PASSWORD     = 30005
    LOGIN_ERROR      = 30006
    COURSE_INFO      = 30008
    SECTION_LABEL    = 30009
    NO_STREAM_ERROR  = 30010
    VMP_WARNING      = 30011

    BUSINESS_ACCOUNT = 30018
    BUSINESS_NAME    = 30019
    PLAYBACK         = 30020
    GENERAL          = 30021
    UTILITY          = 30022
    NEXT_PAGE        = 30023

_ = Language()