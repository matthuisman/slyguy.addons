from slyguy.language import BaseLanguage


class Language(BaseLanguage):
    API_ERROR                = 30003
    ORIGINALS                = 30006
    FULL_DETAILS             = 30007
    HUBS                     = 30008
    IMAX                     = 30009
    SUGGESTED                = 30010
    FEATURED                 = 30011
    EXTRAS                   = 30013
    IA_VER_ERROR             = 30014
    DISNEY_SYNC              = 30016
    PROFILE_WITH_PIN         = 30017
    SKIP_CREDITS             = 30020
    PLAY_NEXT_EPISODE        = 30021
    PLAY_NEXT_MOVIE          = 30022
    DEFAULT_RATIO            = 30023
    SKIP_INTROS              = 30024
    WATCHLIST                = 30026
    ADD_WATCHLIST            = 30027
    DELETE_WATCHLIST         = 30028
    ADDED_WATCHLIST          = 30029
    ENTER_PIN                = 30030
    EMAIL_NOT_FOUND          = 30031
    OTP_INPUT                = 30032
    CONTINUE_WATCHING        = 30042
    NOT_ENTITLED             = 30043
    BAD_CREDENTIALS          = 30044
    COMING_SOON              = 30045
    BAD_PIN                  = 30046
    DISNEY_WATCHLIST         = 30047
    AVAILABLE                = 30049
    AVAILABLE_FORMAT         = 30050
    NO_VIDEO_FOUND           = 30051
    PROFILE_SETTINGS         = 30053
    WIDESCREEN               = 30055


_ = Language()
