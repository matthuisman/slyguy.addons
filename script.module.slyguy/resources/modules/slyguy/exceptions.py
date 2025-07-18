from slyguy import _
from slyguy.constants import ADDON_NAME


class Exit(Exception):
    pass


class Error(Exception):
    def __init__(self, message='', heading=None, show_dialog=True):
        self.message = message
        self.heading = heading or _(_.PLUGIN_ERROR, addon=ADDON_NAME)
        self.show_dialog = show_dialog
        super(Error, self).__init__(message)


class CancelDialog(Exception):
    pass


class InputStreamError(Error):
    pass


class PluginError(Error):
    pass


class GUIError(Error):
    pass


class RouterError(Error):
    pass


class SessionError(Error):
    pass
