from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    ASK_USERNAME             = 30001
    ASK_PASSWORD             = 30002
    API_ERROR                = 30003
    MOVIES                   = 30004
    SERIES                   = 30005
    ORIGINALS                = 30006
    FULL_DETAILS             = 30007
    HUBS                     = 30008
    IMAX                     = 30009
    SUGGESTED                = 30010
    FEATURED                 = 30011
    SEASON                   = 30012
    EXTRAS                   = 30013
    IA_VER_ERROR             = 30014
    DOLBY_VISION             = 30015
    DISNEY_SYNC              = 30016
    PROFILE_WITH_PIN         = 30017
    HDR10                    = 30018
    H265                     = 30019
    SKIP_CREDITS             = 30020
    PLAY_NEXT_EPISODE        = 30021
    PLAY_NEXT_MOVIE          = 30022
    DEFAULT_RATIO            = 30023
    SKIP_INTROS              = 30024
    PLAY_FROM_START          = 30025
    WATCHLIST                = 30026
    ADD_WATCHLIST            = 30027
    DELETE_WATCHLIST         = 30028
    ADDED_WATCHLIST          = 30029
    ENTER_PIN                = 30030
    EMAIL_NOT_FOUND          = 30031
    OTP_INPUT                = 30032
    APP_LANGUAGE             = 30033

    CONTINUE_WATCHING        = 30042
    NOT_ENTITLED             = 30043
    BAD_CREDENTIALS          = 30044
    COMING_SOON              = 30045
    BAD_PIN                  = 30046
    DISNEY_WATCHLIST         = 30047
    PLAY_FROM_TIME           = 30048
    AVAILABLE                = 30049
    AVAILABLE_FORMAT         = 30050
    NO_VIDEO_FOUND           = 30051
    DOLBY_ATMOS              = 30052
    PROFILE_SETTINGS         = 30053
    CONTINUE_WATCHING        = 30054

    WIDESCREEN               = 21377
    TRAILER                  = 20410

_ = Language()
