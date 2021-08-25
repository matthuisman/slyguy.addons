import re

from kodi_six import xbmc

from slyguy import plugin, settings, gui
from slyguy.util import get_kodi_setting, get_addon, run_plugin

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

@plugin.route()
def check_log(**kwargs):
    log_file = xbmc.translatePath('special://logpath/kodi.log')
    with open(log_file, 'rb') as f:
        text = f.read()

    errors = []
    text = text.decode('utf8')
    for line in text.splitlines():
        if 'ERROR <general>:' in line or 'ERROR:' in line:
            if re.search(': [^ :]+ -', line):
                errors.append(line.strip())

    if not errors:
        gui.ok(_.NO_LOG_ERRORS)
    else:
        gui.text('\n'.join(errors), heading=_.LOG_ERRORS)
        if gui.yes_no(_.UPLOAD_LOG):
            addon = get_addon('script.kodi.loguploader', required=True, install=True)
            xbmc.executebuiltin('RunScript(script.kodi.loguploader)')
