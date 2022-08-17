import arrow
import codecs
from kodi_six import xbmc
from slyguy import plugin, gui, signals, inputstream, settings
from slyguy.log import log

from .api import API
from .language import _
from .constants import DEVICE_LINK_URL

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_CHANNELS, _bold=True), path=plugin.url_for(live))
        
        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    options = [
        [_.DEVICE_CODE, _device_code],
    ]

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    gui.refresh()

def _device_code():
    monitor = xbmc.Monitor()
    code = api.device_code()
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=code, url=DEVICE_LINK_URL), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int((i / float(timeout)) * 100))

            if i % 5 == 0 and api.device_login():
                return True

def _art(images, _type='thumb'):
    for row in images:
        if _type == 'thumb' and row['kind'] == 'logo_alternate': #logo
            return row['src']
        elif _type == 'fanart' and row['kind'] == 'default':
            return row['src']

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_CHANNELS)
    
    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for row in api.live_channels():
        folder.add_item(
            label = row['attributes']['name'],
            art = {'thumb': _art(row['images']), 'fanart': _art(row['images'], _type='fanart')},
            playable = True,
            path = plugin.url_for(play_channel, channel_id=row['id'], _is_live=True),
        )

    return folder

@plugin.route()
def play_channel(channel_id, **kwargs):
    url = api.play_channel(channel_id)
    
    return plugin.Item(
        path = url,
        inputstream = inputstream.HLS(live=True),
    )

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for row in api.live_channels():
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=row['id'], logo=_art(row['images']), name=row['attributes']['name'], url=plugin.url_for(play_channel, channel_id=row['id'], _is_live=True)))
