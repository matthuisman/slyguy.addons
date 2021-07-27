from slyguy import plugin, settings, gui
from slyguy.util import get_kodi_setting

from .util import check_updates
from .language import _

@plugin.route('')
def home(**kwargs):
    settings.open()

@plugin.route()
def update_addons(**kwargs):
    num_updates = check_updates(force=True)
    if not num_updates:
        return gui.ok(_.NO_UPDATES)

    try:
        auto_updates = int(get_kodi_setting('general.addonupdates')) == 0
    except:
        auto_updates = False

    if auto_updates:
        gui.ok(_(_.UPDATES_INSTALLED, count=num_updates))
    else:
        gui.ok(_(_.UPDATES_AVAILABLE, count=num_updates))
