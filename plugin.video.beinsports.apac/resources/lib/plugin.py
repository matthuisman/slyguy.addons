import codecs
import time
import re
from xml.sax.saxutils import escape

import arrow
from kodi_six import xbmc
from slyguy import plugin, gui, settings, userdata, signals, inputstream

from .api import API
from .language import _
from .constants import WV_LICENSE_URL, HEADERS

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_CHANNELS, _bold=True), path=plugin.url_for(live_channels))
        folder.add_item(label=_(_.CATCH_UP, _bold=True), path=plugin.url_for(catch_up))
        # folder.add_item(label=_(_.MATCH_HIGHLIGHTS, _bold=True), path=plugin.url_for(catch_up, catalog_id='Match_Highlights', title=_.MATCH_HIGHLIGHTS))
        # folder.add_item(label=_(_.INTERVIEWS, _bold=True),       path=plugin.url_for(catch_up, catalog_id='Interviews', title=_.INTERVIEWS))
        # folder.add_item(label=_(_.SPECIALS, _bold=True),         path=plugin.url_for(catch_up, catalog_id='Specials', title=_.SPECIALS))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    options = [
        [_.DEVICE_CODE, _device_code],
        [_.EMAIL_PASSWORD, _email_password],
    ]

    index = gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    gui.refresh()

def _email_password():
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)

    return True

def _device_code():
    start = time.time()
    data = api.device_code()
    monitor = xbmc.Monitor()

    #qr_code_url = data['ImagePath']

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=data['Code']), heading=_.DEVICE_CODE) as progress:
        while (time.time() - start) < data['ExpireDate']:
            for i in range(5):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / data['ExpireDate']) * 100))

            if api.device_login(data['Code']):
                return True

def _get_logo(url):
    return re.sub('_[0-9]+X[0-9]+.', '.', url)

@plugin.route()
def live_channels(**kwargs):
    folder = plugin.Folder(_.LIVE_CHANNELS)

    for row in api.live_channels():
        folder.add_item(
            label = row['Name'],
            art = {'thumb': _get_logo(row['Logo'])},
            info = {'plot': row.get('Description')},
            path = plugin.url_for(play, channel_id=row['Id'], _is_live=True),
            playable = True,
        )

    return folder

@plugin.route()
def catch_up(catalog_id='CATCHUP', title=_.CATCH_UP, **kwargs):
    folder = plugin.Folder(title)

    for row in api.catch_up(catalog_id=catalog_id):
        program = row['Program']

        fanart = _get_logo(program['Poster'])

        if program.get('Match'):
            art = row['Program']['Match']['LeagueLogo']
        elif program.get('Competition'):
            art = row['Program']['Competition']['Logo']
        else:
            art = row.get('Headline')

        folder.add_item(
            label = row['Name'],
            art = {'fanart': fanart, 'thumb': art},
            info = {'plot': row['Program']['Description']},
            path = plugin.url_for(play, vod_id=row['Id']),
            playable = True,
        )

    return folder

@plugin.route()
@plugin.login_required()
def play(channel_id=None, vod_id=None, **kwargs):
    asset = api.play(channel_id, vod_id)

    _headers = {}
    _headers.update(HEADERS)
    _headers.update({
        'Authorization': asset['DrmToken'],
        'X-CB-Ticket': asset['DrmTicket'],
        'X-ErDRM-Message': asset['DrmTicket'],
    })

    return plugin.Item(
        path = asset['Path'] + '?' + asset['CdnTicket'],
        inputstream = inputstream.Widevine(license_key=WV_LICENSE_URL),
        headers = _headers,
    )

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(plugin.url_for(epg, output='$FILE')))

        for row in api.live_channels():
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=row['Id'], logo=_get_logo(row['Logo']), name=row['Name'],
                    url=plugin.url_for(play, channel_id=row['Id'], _is_live=True)))

@plugin.route()
@plugin.merge()
@plugin.login_required()
def epg(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for row in api.epg(days=settings.getInt('epg_days', 3)):
            channel = row['Channel']

            f.write(u'<channel id="{}"><display-name>{}</display-name><icon src="{}"/></channel>'.format(
                channel['Id'], escape(channel['Name']), escape(_get_logo(channel['Logo']))))

            for program in row['EpgList']:
                f.write(u'<programme channel="{}" start="{}" stop="{}"><title>{}</title><desc>{}</desc></programme>'.format(
                    channel['Id'], arrow.get(program['StartTime']).format('YYYYMMDDHHmmss Z'), arrow.get(program['EndTime']).format('YYYYMMDDHHmmss Z'),
                        escape(program['Name']), escape(program['Description'])))

        f.write(u'</tv>')
