import codecs
import time
from xml.dom.minidom import parseString

import arrow
from kodi_six import xbmc

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.exceptions import PluginError
from slyguy.constants import MIDDLEWARE_PLUGIN, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_START, PLAY_FROM_LIVE

from .api import API
from .language import _
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live))

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

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    gui.refresh()

def _device_code():
    start = time.time()
    data = api.device_code()
    monitor = xbmc.Monitor()
    expires = 300 #5mins
    interval = 5 #check every 5 seconds

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=DEVICE_CODE_URL, code=data['pin']), heading=_.DEVICE_CODE) as progress:
        while (time.time() - start) < expires:
            for i in range(interval):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / expires) * 100))

            if api.device_login(data['pin'], data['anchor']):
                return True

def _email_password():
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)
    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)
    return True

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        if not row['live']:
            continue

        plot = ''
        programs = [row['programmingInfo']['currentProgramme'], row['programmingInfo']['nextProgramme']]
        for epg in programs:
            start = arrow.get(epg['startDate'])
            plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), epg['episode'])

        folder.add_item(
            label = row['title'],
            art = {'thumb': row['programmingInfo']['channelLogoUrl'], 'fanart': row['programmingInfo']['currentProgramme']['thumbnailUrl'], },
            info = {
                'plot': plot,
            },
            playable = True,
            path = plugin.url_for(play, event_id=row['id'], _is_live=True),
        )

    return folder

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.plugin_middleware()
def mpd_request(_data, _path, **kwargs):
    root = parseString(_data)

    mpd = root.getElementsByTagName("MPD")[0]
    # Fixes issues of being too close to head and getting 404s
    mpd.setAttribute('availabilityStartTime', '1970-01-01T00:00:20Z')

    mpd = root.getElementsByTagName("MPD")[0]
    for period in root.getElementsByTagName('Period')[1:]:
        period.parentNode.removeChild(period)

    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

@plugin.route()
@plugin.login_required()
def play(event_id, start=None, play_type=None, **kwargs):
    data, event = api.play(event_id)
    is_live = event.get('live', False)

    headers = HEADERS
    headers.update({
        'Authorization': 'Bearer {}'.format(data['dash']['drm']['jwtToken']),
        'x-drm-info': 'eyJzeXN0ZW0iOiJjb20ud2lkZXZpbmUuYWxwaGEifQ==', #{"system":"com.widevine.alpha"} b64 encoded 
    })

    item = plugin.Item(
        path = data['dash']['url'],
        inputstream = inputstream.Widevine(
            license_key = data['dash']['drm']['url']
        ),
        headers = headers,
        proxy_data = {
            'middleware': {data['dash']['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}},
        }
    )

    if start is None:
        start = arrow.get(event['programmingInfo']['currentProgramme']['startDate']).timestamp
    else:
        start = int(start)
        play_type = PLAY_FROM_START

    offset = arrow.now().timestamp - start
    if is_live and offset > 0:
        offset = (24*3600 - 20) - offset

        if play_type is None:
            play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

        if play_type == PLAY_FROM_ASK:
            result = plugin.live_or_start()
            if result == -1:
                return
            elif result == 1:
                item.resume_from = offset

        elif play_type == PLAY_FROM_START:
            item.resume_from = offset

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for row in api.channels():
            if not row['live']:
                continue

            event_id = row['id']
            channel_id = row['programmingInfo']['channelId']

            catchup = plugin.url_for(play, event_id=event_id, start='{utc}', duration='{duration}')
            catchup = catchup.replace('%7Butc%7D', '{utc}').replace('%7Bduration%7D', '{duration}')

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}" catchup="default" catchup-days="1" catchup-source="{catchup}",{name}\n{url}'.format(
                id=channel_id, logo=row['programmingInfo']['channelLogoUrl'], name=row['title'], url=plugin.url_for(play, event_id=event_id, _is_live=True), catchup=catchup))
