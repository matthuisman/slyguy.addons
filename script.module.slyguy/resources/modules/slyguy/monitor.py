from kodi_six import xbmc

from slyguy import signals
from slyguy.constants import ADDON_ID


class Monitor(xbmc.Monitor):
    def onSettingsChanged(self):
        signals.emit(signals.ON_SETTINGS_CHANGE)

monitor = Monitor()
