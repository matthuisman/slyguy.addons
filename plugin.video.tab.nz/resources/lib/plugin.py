import codecs

from slyguy import plugin, gui, settings, userdata, signals, inputstream

from .api import API
from .language import _
from .constants import *

api = API()

GUEST_SLUGS = {
    'TS1': 'tv.trackside1.m3u8',
    'TS2': 'tv.trackside2.m3u8',
    'TSR': 'radio.or.28.m3u8',
}

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.TRACKSIDE_1, _bold=True), path=plugin.url_for(play, type='channel', id='TS1', _is_live=True), playable=True)
    folder.add_item(label=_(_.TRACKSIDE_2, _bold=True), path=plugin.url_for(play, type='channel', id='TS2', _is_live=True), playable=True)
    folder.add_item(label=_(_.TRACKSIDE_RADIO, _bold=True), path=plugin.url_for(play, type='channel', id='TSR', _is_live=True), playable=True)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_EVENTS, _bold=True), path=plugin.url_for(live_events))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
def play(type, id, **kwargs):
    if type == 'channel' and (id == 'TSR' or not api.logged_in):
        url = 'https://i.mjh.nz/nz/{}'.format(GUEST_SLUGS[id])
    else:
        url = api.access(type, id)

    item = plugin.Item(
        path = url,
        inputstream = inputstream.HLS(live=True, force=True) if id != 'TSR' else None,
        headers = HEADERS,
    )

    return item

@plugin.route()
def live_events(**kwargs):
    folder = plugin.Folder(_.LIVE_EVENTS)

    events = api.live_events()
    for event in events:
        folder.add_item(
            label = event['name'],
            path  = plugin.url_for(play, type='event', id=event['id'], _is_live=True),
            playable = True,
        )

    if not folder.items:
        folder.add_item(label=_(_.NO_EVENTS, _label=True), is_folder=False)

    return folder

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    playlist = u'''#EXTM3U x-tvg-url="{EPG_URL}"
#EXTINF:-1 tvg-id="tv.trackside1" tvg-logo="https://i.mjh.nz/.images/tv.trackside1.png",TAB Trackside 1
{TS1_PATH}
#EXTINF:-1 tvg-id="tv.trackside2" tvg-logo="https://i.mjh.nz/.images/tv.trackside2.png",TAB Trackside 2
{TS2_PATH}
#EXTINF:-1 tvg-id="radio.or.28" tvg-logo="https://i.mjh.nz/.images/radio.or.28.png" radio="true",TAB Trackside Radio
{TSRADIO_PATH}
'''.format(
        EPG_URL = EPG_URL,
        TS1_PATH = plugin.url_for(play, type='channel', id='TS1', _is_live=True),
        TS2_PATH = plugin.url_for(play, type='channel', id='TS2', _is_live=True),
        TSRADIO_PATH = plugin.url_for(play, type='channel', id='TSR', _is_live=True),
    )

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(playlist)
