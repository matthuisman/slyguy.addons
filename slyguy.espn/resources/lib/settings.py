from slyguy import userdata, gui
from slyguy.settings import CommonSettings
from slyguy.settings.types import Bool, Action, Text

from .language import _


def clear_hidden():
    userdata.delete('hidden')
    gui.notification(_.RESET_HIDDEN_OK)


class Settings(CommonSettings):
    SHOW_LIVE_SCORES = Bool('show_live_scores', _.SHOW_LIVE_SCORES, default=False)
    HIDE_ALT_LAN = Bool('alt_languages', _.HIDE_ALT_LAN, default=False)
    EVENT_WHITELIST = Text('sport_whitelist', _.EVENT_WHITELIST)
    CLEAR_HIDDEN = Action(clear_hidden, _.RESET_HIDDEN)


settings = Settings()
