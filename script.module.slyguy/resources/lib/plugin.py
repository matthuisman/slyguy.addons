import re

from kodi_six import xbmc, xbmcaddon
from six.moves.urllib_parse import urlparse

from slyguy import plugin, gui, _
from slyguy.settings.types import STORAGE
from slyguy.util import get_kodi_setting, get_addon
from slyguy.constants import ROUTE_CONTEXT, ROUTE_SETTINGS, ADDON_NAME

from .util import check_updates, get_slyguy_addons


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(_.SETTINGS)

    folder.add_item(
        label = ADDON_NAME,
        path = plugin.url_for(ROUTE_SETTINGS),
        bookmark = False,
    )

    for addon_id in STORAGE.get_addon_ids():
        try:
            addon = xbmcaddon.Addon(addon_id)
        except:
            continue

        folder.add_item(
            label = addon.getAddonInfo('name'),
            art = {'thumb': addon.getAddonInfo('icon')},
            path = plugin.url_for(ROUTE_SETTINGS, _addon_id=addon_id),
            bookmark = False,
        )

    return folder

@plugin.route(ROUTE_CONTEXT)
def context(listitem, **kwargs):
    vid_tag = listitem.getVideoInfoTag()
    trailer_path = vid_tag.getTrailer()

    parsed = urlparse(trailer_path)
    if parsed.scheme.lower() == 'plugin':
        addon_id = parsed.netloc
        get_addon(addon_id, required=True)

    li = plugin.Item(path=trailer_path)
    li.label = u"{} ({})".format(listitem.getLabel(), _.TRAILER)
    li.info = {
        'plot': vid_tag.getPlot(),
        'tagline': vid_tag.getTagLine(),
        'year': vid_tag.getYear(),
        'mediatype': vid_tag.getMediaType(),
    }

    try:
        # v20+
        li.info['genre'] = vid_tag.getGenres()
    except AttributeError:
        li.info['genre'] = vid_tag.getGenre()

    for key in ['thumb','poster','banner','fanart','clearart','clearlogo','landscape','icon']:
        li.art[key] = listitem.getArt(key)

    return li


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
