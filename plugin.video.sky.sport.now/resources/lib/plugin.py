import codecs
import time
from xml.dom.minidom import parseString

import arrow
from kodi_six import xbmc

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.exceptions import PluginError
from slyguy.constants import MIDDLEWARE_PLUGIN, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_START, PLAY_FROM_LIVE, LIVE_HEAD, ROUTE_LIVE_TAG

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

        folder.add_item(label=_(_.HOME, _bold=True), path=plugin.url_for(content, content_id='home', label=_.HOME))
        folder.add_item(label=_(_.SPORTS, _bold=True), path=plugin.url_for(content, content_id='browse', label=_.SPORTS))
     #   folder.add_item(label=_(_.REPLAYS, _bold=True), path=plugin.url_for(replays))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

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
def content(content_id, label, **kwargs):
    folder = plugin.Folder(label)
    data = api.page(content_id)
    items = process_rows(data['buckets'], content_id=content_id)
    folder.add_items(items)
    return folder

@plugin.route()
def vod_playlist(playlist_id, **kwargs):
    data = api.playlist(playlist_id)
    folder = plugin.Folder(data['title'])
    items = process_rows(data['videos'].get('vods', []))
    folder.add_items(items)
    return folder

@plugin.route()
@plugin.pagination('last_seen')
def bucket(content_id, bucket_id, last_seen=None, **kwargs):
    data = api.bucket(content_id, bucket_id, last_seen=last_seen)

    folder = plugin.Folder(data['name'])
    items = process_rows(data['contentList'])
    folder.add_items(items)

    return folder, data['paging']['lastSeen'] if data['paging']['moreDataAvailable'] else None

@plugin.route()
@plugin.search()
def search(query, page=1, **kwargs):
    data = api.search(query, page=page)
    return process_rows(data['hits']), data['nbPages'] > page+1

def process_rows(rows, content_id=None):
    items = []
    for row in rows:
        if 'rowTypeData' in row and row['contentList']: #BUCKET DONE
            if row['type'] in ('UPCOMING','EPG_NOW_NEXT','LIVE','VOD_RESUME'):
                continue

            item = plugin.Item(
                label = row['name'],
                path = plugin.url_for(bucket, content_id=content_id, bucket_id=row['exid']),
                info = {
                    'plot': row['rowTypeData'].get('description'),
                },
                art = {'fanart': row['rowTypeData']['background'].get('imageUrl')},
            )

        elif row['type'] in ('SECTION_LINK',): #DONE
            item = plugin.Item(
                label = row['title'],
                art = {'thumb': row['thumbnailUrl'] if not row['thumbnailUrl'].lower().endswith('.svg') else None},
                path = plugin.url_for(content, content_id=row['sectionName'], label=row['title']),
            )

        elif row['type'] in ('PLAYLIST',):  #DONE
            item = plugin.Item(
                label = row['title'],
                art = {'thumb': row['smallCoverUrl'].replace('/original/', '/346x380/'), 'fanart': row['coverUrl'].replace('/original/', '/1920x1080/')},
                #info = {'plot': str(row['vodCount'])},
                path = plugin.url_for(vod_playlist, playlist_id=row['id']),
            )

        elif row['type'] in ('VOD', 'VOD_VIDEO'): #DONE
            item = plugin.Item(
                label = row.get('title') or row.get('name'),
                art = {'thumb': row['thumbnailUrl']},
                info = {
                    'plot': row['description'],
                    'duration': row['duration'],
                },
                playable = True,
                path = plugin.url_for(play_vod, vod_id=row['id']),
            )

        elif row['type'] in ('EPG',):  #DONE
            plot = ''
            for epg in row['programmes']:
                start = arrow.get(epg['startDate'])
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), epg['episode'])

            item = plugin.Item(
                label = row['title'],
                art = {'thumb': row['logoUrl'], 'fanart': row['programmes'][0]['thumbnailUrl']},
                info = {
                    'plot': plot,
                },
                playable = True,
                path = plugin.url_for(play_event, event_id=row['liveEventId'], _is_live=True),
            )

        elif row['type'] in ('LIVE',) and 'programmingInfo' in row:  #DONE
            plot = ''
            programs = [row['programmingInfo']['currentProgramme'], row['programmingInfo']['nextProgramme']]
            for epg in programs:
                start = arrow.get(epg['startDate'])
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), epg['episode'])

            item = plugin.Item(
                label = row['title'],
                art = {'thumb': row['programmingInfo']['channelLogoUrl'], 'fanart': row['programmingInfo']['currentProgramme']['thumbnailUrl'], },
                info = {
                    'plot': plot,
                },
                playable = True,
                path = plugin.url_for(play_event, event_id=row['id'], _is_live=True),
            )

        elif row['type'] in ('REPLAY',):  #DONE
            item = plugin.Item(
                label = row['startDate'].to('local').humanize() + ' - ' + row['episode'],
                art = {'thumb': row['thumbnailUrl']},
                info = {
                    'plot': u'[B]{}[/B]\n\n{}'.format(row['channel']['title'], row['description']),
                    'duration': (row['endDate'] - row['startDate']).total_seconds(),
                },
                playable = True,
                path = plugin.url_for(play_event, event_id=row['channel']['id'], start=row['startDate'].timestamp, _is_live=True),
            )
        else:
            continue

        items.append(item)
    return items

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    channels = [x for x in api.channels() if x['live']]
    items = process_rows(channels)
    folder.add_items(items)
    return folder

@plugin.route()
def replays(**kwargs):
    folder = plugin.Folder(_.REPLAYS)

    channels = {str(x['programmingInfo']['channelId']): x for x in api.channels() if x['live']}

    now = arrow.now()
    start = now.shift(days=-1)
    epg = api.epg(list(channels.keys()), start, now)

    programs = []
    for channel_id, rows in epg.items():
        for row in rows:
            row['type'] = 'REPLAY'
            row['channel_id'] = str(channel_id)
            row['startDate'] = arrow.get(row['startDate'])
            row['endDate'] = arrow.get(row['endDate'])
            if row['channel_id'] not in channels or row['endDate'] > now or row['startDate'] < start:
                continue
            row['channel'] = channels[row['channel_id']]
            programs.append(row)

    programs = sorted(programs, key=lambda x: (x['startDate'], x['channel_id']), reverse=True)
    items = process_rows(programs)
    folder.add_items(items)
    return folder

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.plugin_middleware()
def mpd_request(_data, _path, live=False, **kwargs):
    root = parseString(_data)

    mpd = root.getElementsByTagName("MPD")[0]

    # IA doesnt support multi-period with different baseurls in rep (https://github.com/xbmc/inputstream.adaptive/issues/1500)
    # For now, lets remove all periods except the latest
    if live:
        periods_to_remove = [x for x in root.getElementsByTagName('Period')][:-1]
        if periods_to_remove:
            for period in periods_to_remove:
                period.parentNode.removeChild(period)
            mpd.setAttribute('timeShiftBufferDepth', 'PT300S')

    # Fixes issues of being too close to head and getting 404 error
    seconds_diff = 0
    utc = mpd.getElementsByTagName("UTCTiming")
    if utc:
        utc_time = arrow.get(utc[0].getAttribute('value'))
        seconds_diff = max((arrow.now() - utc_time).total_seconds(), 0)

    avail = mpd.getAttribute('availabilityStartTime')
    if avail:
        seconds_diff += 30
        avail_start = arrow.get(avail).shift(seconds=seconds_diff)
        mpd.setAttribute('availabilityStartTime', avail_start.format('YYYY-MM-DDTHH:mm:ss'+'Z'))

    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

@plugin.route()
@plugin.login_required()
def play_event(event_id, start=None, play_type=None, **kwargs):
    data, event = api.play_event(event_id)
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
            'middleware': {data['dash']['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request, live=True),}},
        }
    )

    # if start is None:
    #     start = arrow.get(event['programmingInfo']['currentProgramme']['startDate']).timestamp
    # else:
    #     start = int(start)
    #     play_type = PLAY_FROM_START

    # offset = arrow.now().timestamp - start
    # if is_live and offset > 0:
    #     offset = (24*3600 + 20) - offset

    #     if play_type is None:
    #         play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

    #     if play_type == PLAY_FROM_ASK:
    #         result = plugin.live_or_start()
    #         if result == -1:
    #             return
    #         elif result == 1:
    #             item.resume_from = max(1, offset)

    #     elif play_type == PLAY_FROM_START:
    #         item.resume_from = max(1, offset)

    # if not item.resume_from and ROUTE_LIVE_TAG in kwargs:
    #     ## Need below to seek to live over multi-periods
    #     item.resume_from = LIVE_HEAD

    return item

@plugin.route()
@plugin.login_required()
def play_vod(vod_id, **kwargs):
    data, vod = api.play_vod(vod_id)

    headers = HEADERS
    headers.update({
        'Authorization': 'Bearer {}'.format(data['dash'][0]['drm']['jwtToken']),
        'x-drm-info': 'eyJzeXN0ZW0iOiJjb20ud2lkZXZpbmUuYWxwaGEifQ==', #{"system":"com.widevine.alpha"} b64 encoded 
    })

    item = plugin.Item(
        path = data['dash'][0]['url'],
        inputstream = inputstream.Widevine(
            license_key = data['dash'][0]['drm']['url']
        ),
        headers = headers,
        proxy_data = {
            'middleware': {data['dash'][0]['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}},
        }
    )

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

            catchup = plugin.url_for(play_event, event_id=event_id, start='{utc}', duration='{duration}', _is_live=True)
            catchup = catchup.replace('%7Butc%7D', '{utc}').replace('%7Bduration%7D', '{duration}')

            if catchup:
                catchup = ' catchup="default" catchup-days="1" catchup-source="{}"'.format(catchup)
            else:
                catchup = ''

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}"{catchup},{name}\n{url}'.format(
                id=channel_id, logo=row['programmingInfo']['channelLogoUrl'], name=row['title'], 
                catchup=catchup, url=plugin.url_for(play_event, event_id=event_id, play_type=PLAY_FROM_LIVE, _is_live=True),
            ))
