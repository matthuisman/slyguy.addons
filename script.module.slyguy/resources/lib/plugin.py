import re

from kodi_six import xbmc

from slyguy import plugin, gui
from slyguy.util import get_kodi_setting, get_addon

from .util import check_updates, get_slyguy_addons
from .language import _


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
    for addon_id in updates:
        update = updates[addon_id]
        text += u'{} {} > {}\n'.format(update['name'], update['cur'], update['new'])
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

    addon_ids = [x.lower() for x in get_slyguy_addons()]

    errors = []
    text = text.decode('utf8', errors='ignore')
    for line in text.splitlines():
        match = None
        if 'ERROR <general>:' in line: #Kodi 19+
            match = re.search('ERROR <general>: ([^ :-]+?) -', line)
        elif 'ERROR:' in line: #Kodi 18
            match = re.search('ERROR: ([^ :-]+?) -', line)

        if match and match.group(1) in addon_ids:
            errors.append(line.strip())

    if not errors:
        gui.ok(_.NO_LOG_ERRORS)
    else:
        gui.text('\n'.join(errors), heading=_.LOG_ERRORS)
        if gui.yes_no(_.UPLOAD_LOG):
            addon = get_addon('script.kodi.loguploader', required=True, install=True)
            xbmc.executebuiltin('RunScript(script.kodi.loguploader)')
