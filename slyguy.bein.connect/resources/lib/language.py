from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME             = 30001
    ASK_PASSWORD             = 30002
    LIVE_CHANNELS            = 30003
    LOGIN_ERROR              = 30004
    DEVICE_LABEL             = 30005
    SELECT_DEVICE            = 30006
    NEW_DEVICE               = 30007
    REMOVE_DEVICE            = 30008
    DEVICE_NAME              = 30009
    SELECT_REMOVE_DEVICE     = 30010
    REMOVE_CONFIRM           = 30011
    NEW_CONFIRM              = 30012
    GEO_BLOCKED              = 30013
    HTTP_ERROR               = 30014
    LOGIN_TYPE               = 30015
    LOGIN_MULTI_IP           = 30016
    LOGIN_MULTI_DEVICE       = 30017
    LOGIN_PASSWORD           = 30018
    TOKEN_ERROR              = 30019
    LOGIN_MULTI_IP_ERROR     = 30020
    LOGIN_MULTI_DEVICE_ERROR = 30021
    SETTINGS_ERROR           = 30022
    DEFAULT_LANGUAGE         = 30023

_ = Language()