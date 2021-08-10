from slyguy import plugin, settings, gui
from slyguy.util import get_kodi_setting

from .util import check_updates
from .language import _

@plugin.route('')
def home(**kwargs):
    settings.open()

@plugin.route()
def update_addons(**kwargs):
    updates = check_updates(force=True)
    if not updates:
        return gui.ok(_.NO_UPDATES)

    try:
        auto_updates = int(get_kodi_setting('general.addonupdates')) == 0
    except:
        auto_updates = False

    text = u''
    for update in updates:
        text += u'{} {} > {}\n'.format(update[0].getAddonInfo('name'), update[1], update[2])
    text = text.rstrip()

    if auto_updates:
        text = _(_.UPDATES_INSTALLED, count=len(updates), updates=text)
    else:
        text = _(_.UPDATES_AVAILABLE, count=len(updates), updates=text)

    gui.text(text)
