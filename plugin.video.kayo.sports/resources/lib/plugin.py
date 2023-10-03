import codecs
import time

import arrow
from kodi_six import xbmc

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.log import log
from slyguy.exceptions import PluginError
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_RESUME_TAG, ROUTE_LIVE_TAG, LIVE_HEAD

from .api import API
from .language import _
from .constants import *
from streamotion.constants import *

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
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(landing, title=_.FEATURED, name='home' if api.is_subscribed() else 'free'))
        folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(landing, title=_.SHOWS, name='shows'))
        folder.add_item(label=_(_.SPORTS, _bold=True), path=plugin.url_for(landing, title=_.SPORTS, name='sports'))
        folder.add_item(label=_(_.LIVE_CHANNELS, _bold=True), path=plugin.url_for(live))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)
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

    _select_profile()
    gui.refresh()

def _device_code():
    start = time.time()
    data = api.device_code()
    monitor = xbmc.Monitor()

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=CODE_URL, code=data['user_code']), heading=_.DEVICE_CODE) as progress:
        while (time.time() - start) < data['expires_in']:
            for i in range(data['interval']):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / data['expires_in']) * 100))

            if api.device_login(data['device_code']):
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

def _live_channels():
    href = None
    for row in api.landing('sports')['panels']:
        if 'live channels' in row['title'].lower():
            href = row['links']['panels']
            break

    if not href:
        raise PluginError(_.LIVE_PANEL_ID_MISSING)

    channels = []
    data = api.panel(href)
    live_data = api.channel_data()

    for row in data.get('contents', []):
        if row['contentType'] != 'video':
            continue

        row['data']['chno'] = None
        row['data']['epg'] = []
        if row['data']['id'] in live_data:
            row['data']['chno'] = live_data[row['data']['id']]['chno']
            row['data']['epg'] = live_data[row['data']['id']]['epg']

        channels.append(row['data'])

    return sorted(channels, key=lambda x: (x is None, x['chno'] or 9999))

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_CHANNELS)
    show_chnos = settings.getBool('show_chnos', True)

    if settings.getBool('show_epg', True):
        now = arrow.now()
        epg_count = 5
    else:
        epg_count = None

    for channel in _live_channels():
        item = _parse_video(channel)
        if not item:
            continue

        if channel['chno'] and show_chnos:
            item.label = _(_.LIVE_CHNO, chno=channel['chno'], label=item.label)

        plot = u''
        if epg_count:
            count = 0
            for index, row in enumerate(channel.get('epg', [])):
                start = arrow.get(row[0])
                try: stop = arrow.get(channel['epg'][index+1][0])
                except: stop = start.shift(hours=1)

                if (now > start and now < stop) or start > now:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                    count += 1
                    if count == epg_count:
                        break

        if plot:
            item.info['plot'] = plot

        folder.add_items(item)

    return folder

@plugin.route()
@plugin.login_required()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('avatar')
    userdata.delete('profile_name')
    userdata.delete('profile_id')
    gui.refresh()

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query=query, page=page)['panels'][0]
    return _parse_contents(data.get('contents', [])), data['resultCount'] > 250

@plugin.route()
def season(show_id, season_id, title, **kwargs):
    return _season(show_id, season_id, title)

def _season(show_id, season_id, title):
    data = api.show(show_id=show_id, season_id=season_id)
    folder = plugin.Folder(title)

    for row in data['panels']:
        if row['title'] == 'Episodes':
            folder.add_items(_parse_contents(row.get('contents', [])))

    return folder

@plugin.route()
def show(show_id, title, **kwargs):
    data = api.show(show_id=show_id)

    folder = plugin.Folder(title)

    for row in data['panels']:
        if row['title'] == 'Seasons':
            # flatten
            if len(row.get('contents', [])) == 1:
                data = row['contents'][0]['data']
                return _season(show_id, data['id'], title)

            for row2 in row.get('contents', []):
                data = row2['data']

                folder.add_item(
                    label = data['contentDisplay']['title']['value'],
                    art  = {
                        'thumb': _get_image(data, 'thumb'),
                        'fanart': _get_image(data, 'fanart'),
                    },
                    info = {
                        'plot': data['contentDisplay']['synopsis'] or None,
                    },
                    path = plugin.url_for(season, show_id=show_id, season_id=data['id'], title=data['contentDisplay']['title']['value']),
                )

    return folder

@plugin.route()
def panel(href, **kwargs):
    data = api.panel(href)
    folder = plugin.Folder(data['title'])
    folder.add_items(_parse_contents(data.get('contents', [])))
    return folder

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    _select_profile()
    gui.refresh()

def _select_profile():
    profiles = api.profiles()

    options = []
    values  = []
    default = -1

    avatars = {}
    for avatar in api.profile_avatars():
        avatars[avatar['id']] = avatar['url']

    for index, profile in enumerate(profiles):
        profile['avatar'] = avatars.get(profile['avatar_id'])

        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': profile['avatar']}))

        if profile['id'] == userdata.get('profile_id'):
            default = index
            _set_profile(profile, notify=False)

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _set_profile(profile, notify=True):
    userdata.set('avatar', profile['avatar'])
    userdata.set('profile_name', profile['name'])
    userdata.set('profile_id', profile['id'])

    if notify:
        gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=profile['avatar'])

@plugin.route()
def landing(title, name, sport=None, series=None, team=None, **kwargs):
    folder = plugin.Folder(title)

    for index, row in enumerate(api.landing(name, sport=sport, series=series, team=team)['panels']):
        is_hero = row['panelType'] == 'hero-carousel' and ('hero' in row['title'].lower() or index == 0)
        
        if 'id' not in row or (is_hero and not settings.getBool('show_hero_contents', True)):
            continue

        if 'live channels' in row['title'].lower():
            folder.add_item(
                label = row['title'],
                path  = plugin.url_for(live),
            )

        elif is_hero or row['panelType'] == 'nav-menu':
            row['contents'] = row.get('contents') or api.panel(row['links']['panels']).get('contents', [])
            folder.add_items(_parse_contents(row['contents']))

        elif row['panelType'] not in ('nav-menu-sticky',):
            folder.add_item(
                label = row['title'],
                path  = plugin.url_for(panel, href=row['links']['panels']),
            )

    return folder

def _parse_contents(rows):
    items = []

    for row in rows:
        if row['contentType'] == 'video':
            items.append(_parse_video(row['data']))

        elif row['contentType'] == 'section':
            items.append(_parse_section(row['data']))

    return items

def _parse_section(data):
    if data['type'] == 'panel':
        path = plugin.url_for(landing,
                title = data['clickthrough']['title'],
                name = data['clickthrough']['type'],
                sport = data['clickthrough']['sportId'] or None,
                series = data['clickthrough']['seriesId'] or None,
                team = data['clickthrough']['teamId'] or None,
                )
    else:
        path = plugin.url_for(show, show_id=data['id'], title=data['clickthrough']['title'])

    return plugin.Item(
        label = data['clickthrough']['title'],
        art = {
            'thumb': _get_image(data, 'thumb'),
            'fanart': _get_image(data, 'fanart'),
        },
        info = {
            'plot': data['contentDisplay']['synopsis'] or None,
        },
        path = path,
    )

def _get_image(data, img_type='thumb', width=None):
    thumb_keys = ['tile',]
    fanart_keys = ['hero-default', 'hero', 'heroPortrait']

    if img_type == 'thumb':
        for key in thumb_keys:
            if key in data['contentDisplay']['images']:
                return data['contentDisplay']['images'][key].replace('${WIDTH}', width or '612')

    elif img_type == 'fanart':
        for key in fanart_keys:
            if key in data['contentDisplay']['images']:
                return data['contentDisplay']['images'][key].replace('${WIDTH}', width or '1920')

def _makeTime(start=None):
    return start.to('local').format('h:mmA') if start else ''

def _makeDate(now, start=None):
    if not start:
        return ''

    if now.year == start.year:
        return start.to('local').format('DD MMM')
    else:
        return start.to('local').format('DD MMM YY')

def _makeHumanised(now, start=None):
    if not start:
        return ''

    now = now.to('local').replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    start = start.to('local').replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    days = (start - now).days

    if days == -1:
        return 'yesterday'
    elif days == 0:
        return 'today'
    elif days == 1:
        return 'tomorrow'
    elif days <= 7 and days >= 1:
        return start.format('dddd')
    else:
        return _makeDate(now, start)

def _parse_video(data):
    clickthrough = data['clickthrough']
    content = data['contentDisplay']

    now = arrow.now()
    start = arrow.get(clickthrough['transmissionTime'])
    precheck = start

    if clickthrough.get('preCheckTime'):
        precheck = arrow.get(clickthrough['preCheckTime'])
        if precheck > start:
            precheck = start

    title = clickthrough['title']
    if content.get('headline').strip():
        title += ' [' + content['headline'].replace('${DATE_HUMANISED}', _makeHumanised(now, start).upper()).replace('${TIME}', _makeTime(start)) + ']'

    if not api.is_subscribed():
        is_free = content.get('isFreemium', False)

        if settings.getBool('hide_locked', False) and not is_free:
            return None
        elif not is_free:
            title = _(_.LOCKED, label=title)

    item = plugin.Item(
        label = title,
        art  = {
            'thumb' : _get_image(data, 'thumb'),
            'fanart': _get_image(data, 'fanart'),
        },
        info = {
            'plot': content['synopsis'] or None,
            'mediatype': 'video',
        },
        playable = True,
    )

    is_live = False
    play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

    start_from = ((start - precheck).seconds)
    if start_from < 1:
        start_from = 1

    if now < start:
        is_live = True

    elif data['type'] == 'live-linear':
        is_live = True
        start_from = 0
        play_type = PLAY_FROM_LIVE

    elif data['playback']['info']['playbackType'] == 'LIVE' and clickthrough.get('isStreaming', False):
        is_live = True

        item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
            plugin.url_for(play, id=data['id'], play_type=PLAY_FROM_LIVE, _is_live=is_live)
        )))

        item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
            plugin.url_for(play, id=data['id'], start_from=start_from, play_type=PLAY_FROM_START, _is_live=is_live)
        )))

    item.path = plugin.url_for(play, id=data['id'], start_from=start_from, play_type=play_type, _is_live=is_live)

    return item

@plugin.route()
@plugin.plugin_request()
def license_request(_path, _data, **kwargs):
    data = api.license_request(_data)
    with open(_path, 'wb') as f:
        f.write(data)
    return {'url': _path}

@plugin.route()
@plugin.login_required()
def play(id, start_from=0, play_type=PLAY_FROM_LIVE, **kwargs):
    start_from = int(start_from)
    play_type = int(play_type)
    is_live = ROUTE_LIVE_TAG in kwargs

    if is_live:
        if play_type == PLAY_FROM_LIVE:
            start_from = 0
        elif play_type == PLAY_FROM_ASK:
            start_from = plugin.live_or_start(start_from)
            if start_from == -1:
                return

    asset = api.stream(id)
    streams = [asset['recommendedStream']]
    streams.extend(asset['alternativeStreams'])
    log.debug('Available stream formats: {}'.format(set([x['mediaFormat'] for x in streams])))
    log.debug('Supported stream formats: {}'.format(SUPPORTED_FORMATS))
    streams = [s for s in streams if s['mediaFormat'] in SUPPORTED_FORMATS]
    if not streams:
        raise PluginError(_.NO_STREAM)

    prefer_cdn = settings.getEnum('prefer_cdn', AVAILABLE_CDNS)
    prefer_format = SUPPORTED_FORMATS[0]

    if prefer_cdn == CDN_AUTO:
        try:
            data = api.use_cdn(is_live)
            prefer_cdn = data['useCDN']

            prefer_format = data['drm_mediaformat'] if data['drm_enabled'] else data['mediaFormat']
            if data['ssai']:
                prefer_format = 'ssai-' + prefer_format

            if prefer_format.startswith('ssai-'):
                log.debug('Stream Format: Ignoring prefer ssai format')
                prefer_format = prefer_format[5:]
        except Exception as e:
            log.debug('Failed to get preferred cdn')
            prefer_cdn = AVAILABLE_CDNS[0]

    providers = [prefer_cdn]
    providers.extend([s['provider'] for s in streams])

    formats = [prefer_format]
    formats.extend(SUPPORTED_FORMATS)

    streams = sorted(streams, key=lambda k: (providers.index(k['provider']), formats.index(k['mediaFormat'])))
    stream = streams[0]

    log.debug('Stream CDN: {provider} | Stream Format: {mediaFormat}'.format(**stream))

    item = plugin.Item(
        path = stream['manifest']['uri'],
        headers = PLAY_HEADERS,
    )

    ## Cloudfront streams start from correct position
    if stream['provider'] == CDN_CLOUDFRONT and start_from:
        start_from = 1

    if stream['mediaFormat'] in (FORMAT_DASH, FORMAT_DASH_SSAI):
        item.inputstream = inputstream.MPD()

    elif stream['mediaFormat'] in (FORMAT_HLS_TS, FORMAT_HLS_TS_SSAI):
        force = stream['mediaFormat'] == FORMAT_HLS_TS_SSAI or (is_live and play_type == PLAY_FROM_LIVE and asset['assetType'] != 'live-linear')
        item.inputstream = inputstream.HLS(force=force, live=is_live)
        if force and not item.inputstream.check():
            raise PluginError(_.HLS_REQUIRED)

    elif stream['mediaFormat'] in (FORMAT_HLS_FMP4, FORMAT_HLS_FMP4_SSAI):
        ## No audio on ffmpeg or IA
        item.inputstream = inputstream.HLS(force=True, live=is_live)
        if not item.inputstream.check():
            raise PluginError(_.HLS_REQUIRED)

    elif stream['mediaFormat'] in (FORMAT_DRM_DASH, FORMAT_DRM_DASH_SSAI, FORMAT_DRM_DASH_HEVC, FORMAT_DRM_DASH_HEVC_SSAI):
        item.inputstream = inputstream.Widevine(
            license_key=plugin.url_for(license_request),
        )

    if start_from and not ROUTE_RESUME_TAG in kwargs:
        item.resume_from = start_from

    if not item.resume_from and ROUTE_LIVE_TAG in kwargs:
        ## Need below to seek to live over multi-periods
        item.resume_from = LIVE_HEAD

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for row in _live_channels():
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" channel-id="kayo-{id}" tvg-chno="{channel}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=row['id'], channel=row['chno'] or '', logo=_get_image(row, 'thumb'),
                    name=row['clickthrough']['title'], url=plugin.url_for(play, id=row['id'], _is_live=True)))
