from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    DEVICE_LINK       = 30001
    DEVICE_LINK_STEPS = 30002
    DEVICE_ID         = 30003
    API_ERROR         = 30004
    GO_TO_SERIES      = 30005
    NO_VIDEO_FOUND    = 30006

    L1_SECURE_DEVICE  = 30009
    PLAY_NEXT_EPISODE = 30010
    SKIP_INTROS       = 30011
    PLAY_NEXT_MOVIE   = 30012
    SKIP_CREDITS      = 30013
    INFORMATION       = 19033
    H265              = 30014
    ENABLE_4K         = 30015
    DOLBY_VISION      = 30016

_ = Language()