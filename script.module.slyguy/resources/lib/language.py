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
    AUTO              = 30008
    WV_LEVEL_L1       = 30009
    WV_LEVEL_L3       = 30010
    HDCP_LEVEL        = 30011
    HDCP_NONE         = 30012
    HDCP_1            = 30013
    HDCP_2_2          = 30014
    HDCP_3_0          = 30015
    NO_LOG_ERRORS     = 30016
    LOG_ERRORS        = 30017
    UPLOAD_LOG        = 30018
    CHECK_LOG         = 30019
    DONOR_ID          = 30020
    SHOW_NEWS         = 30021
    VIDEO_MEDIA       = 30023
    SHOW_FOLDERS      = 30024
    ARCH_CHANGED      = 30036
    VIDEO_MENUS       = 30037
    FAST_UPDATES      = 30040

_ = Language()
