from slyguy.language import BaseLanguage

class Language(BaseLanguage):
    LIVE                 = 30001
    PLAYED               = 30002
    UPCOMING             = 30003
    ASK_USERNAME         = 30006
    ASK_PASSWORD         = 30007
    LOGIN_ERROR          = 30008
    REMINDER_SET         = 30010
    REMINDER_REMOVED     = 30011
    PLAY_ERROR           = 30012
    NO_GAMES             = 30013
    ERROR_GAME_NOT_FOUND = 30014
    SET_REMINDER         = 30015
    REMOVE_REMINDER      = 30016
    WATCH_LIVE           = 30017
    WATCH_FROM_START     = 30018
    FULL_GAME            = 30019
    CONDENSED_GAME       = 30020
    SHOW_SCORE           = 30021
    STREAM_STARTED       = 30022
    KICKOFF              = 30023
    WATCH                = 30024
    CLOSE                = 30025
    REMINDER_TYPE        = 30026
    POP_UP_DIALOG        = 30027
    NOTIFCATION          = 30028
    REMINDER_WHEN        = 30029
    STREAM_STARTS        = 30030
    KICK_OFF_TIME        = 30031
    SHOW_SCORES          = 30032
    AFTER_X_HOURS        = 30033


    A_DRAW               = 30036
    X_WINS               = 30037
    GEO_ERROR            = 30038
    GAME_DESC            = 30039
    KICK_OFF             = 30040
    GAME_TITLE           = 30041
    NO_ACCESS            = 30042
    GEO_HEADING          = 30043
    LIVE_PLAY_TYPE       = 30044

    PLAY_FROM            = 30048
    HLS_REQUIRED         = 30049
    GAMES_ERROR          = 30050

    NEXT_PAGE            = 30059

_ = Language()