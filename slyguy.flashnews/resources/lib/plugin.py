import codecs
import time
import re

import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.log import log
from slyguy.monitor import monitor
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_TAG, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, LIVE_HEAD, ROUTE_RESUME_TAG

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
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        # folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(landing, slug='home', title=_.FEATURED))
        # folder.add_item(label=_(_.CHANNELS, _bold=True), path=plugin.url_for(landing, slug='channels', title=_.CHANNELS))
        # folder.add_item(label=_(_.CATEGORIES, _bold=True), path=plugin.url_for(landing, slug='categories', title=_.CATEGORIES))
        folder.add_item(label=_(_.LIVE_CHANNELS, _bold=True), path=plugin.url_for(live))
        # folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': _get_avatar(userdata.get('avatar_id'))}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)
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
    with gui.progress(_(_.DEVICE_LINK_STEPS, url=data['verification_uri'], code=data['user_code']), heading=_.DEVICE_CODE) as progress:
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
    data = None
    for row in api.landing('channels')['panels']:
        if 'by news channel' in row['title'].lower():
            data = row
            break

    if not data:
        raise PluginError(_.LIVE_PANEL_ID_MISSING)

    if not data.get('contents', []):
        data = api.panel(panel_id=row['id'])

    channels = []
    live_data = api.channel_data()

    for row in data.get('contents', []):
        channel_id = row['data']['contentDisplay']['linearProvider']
        if not channel_id:
            continue

        row['data']['chno'] = None
        row['data']['epg'] = []
        if channel_id in live_data:
            row['data'].update(live_data[channel_id])
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
        item = plugin.Item(
            label = channel['contentDisplay']['title']['value'],
            playable = True,
            art = {
                'thumb': channel['contentDisplay']['images']['menuItemSelected'].replace('${WIDTH}', '800'),
            },
            path = plugin.url_for(play_channel, channel_id=channel['contentDisplay']['linearProvider'], _is_live=True),
        )

        if channel['chno'] and show_chnos:
            item.label = _(_.LIVE_CHNO, chno=channel['chno'], label=item.label)

        plot = u''
        count = 0
        if epg_count:
            for index, row in enumerate(channel.get('epg', [])):
                start = arrow.get(row[0])
                try: stop = arrow.get(channel['epg'][index+1][0])
                except: stop = start.shift(hours=1)

                if (now > start and now < stop) or start > now:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                    count += 1
                    if count == epg_count:
                        break

        if not count:
            plot += channel.get('description', '')

        item.info['plot'] = plot
        folder.add_items(item)

    return folder

@plugin.route()
@plugin.login_required()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('avatar_id')
    userdata.delete('profile_name')
    userdata.delete('profile_id')
    gui.refresh()

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    if _select_profile() == False:
        gui.ok(_.NO_PROFILES)
    gui.refresh()

def _select_profile():
    options = []
    values  = []
    default = -1

    profiles = api.profiles()
    if not profiles:
        return False

    for index, profile in enumerate(profiles):
        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': _get_avatar(profile['avatar_id'])}))

        if profile['id'] == userdata.get('profile_id'):
            default = index
            _set_profile(profile, notify=False)

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _get_avatar(avatar_id):
    if avatar_id is None:
        return None

    return AVATAR_URL.format(avatar_id=avatar_id)

def _set_profile(profile, notify=True):
    userdata.set('avatar_id', profile['avatar_id'])
    userdata.set('profile_name', profile['name'])
    userdata.set('profile_id', profile['id'])

    if notify:
        gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=_get_avatar(profile['avatar_id']))

@plugin.route()
@plugin.login_required()
def play_channel(channel_id, **kwargs):
    data = api.panel(panel_id=LINEAR_CHANNEL_PANEL_ID, channel_id=channel_id)
    asset_id = data['contents'][0]['data']['clickthrough']['assetPlay']
    return _play(asset_id, **kwargs)

def _play(id, start_from=0, play_type=PLAY_FROM_LIVE, **kwargs):
    start_from = int(start_from)
    play_type = int(play_type)
    is_live = ROUTE_LIVE_TAG in kwargs

    if is_live:
        if play_type == PLAY_FROM_LIVE:
            start_from = 0
        elif play_type == PLAY_FROM_ASK:
            start_from = plugin.live_or_start(start_from or 1)
            if start_from == -1:
                return

    asset = api.stream(id)
    streams = [asset['recommendedStream']]
    streams.extend(asset['alternativeStreams'])
    streams = [s for s in streams if s['mediaFormat'] in SUPPORTED_FORMATS]
    if not streams:
        raise PluginError(_.NO_STREAM)

    prefer_cdn = settings.getEnum('prefer_cdn', AVAILABLE_CDNS)
    prefer_format = SUPPORTED_FORMATS[0]

    if prefer_cdn == CDN_AUTO:
        try:
            data = api.use_cdn(is_live)
            prefer_cdn = data['useCDN']
            prefer_format = 'ssai-{}'.format(data['mediaFormat']) if data['ssai'] else data['mediaFormat']
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
        headers = HEADERS,
    )

    item.headers.update({'authorization': 'Bearer {}'.format(userdata.get('access_token'))})

    if stream['mediaFormat'] == FORMAT_DASH:
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

    elif stream['mediaFormat'] in (FORMAT_DRM_DASH, FORMAT_DRM_DASH_HEVC):
        item.inputstream = inputstream.Widevine(
            license_key = LICENSE_URL,
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

        for channel in _live_channels():
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" channel-id="{channel}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=channel['contentDisplay']['linearProvider'], channel=channel['chno'] or '', logo=channel['contentDisplay']['images']['menuItemSelected'].replace('${WIDTH}', '800'),
                    name=channel['contentDisplay']['title']['value'], url=plugin.url_for(play_channel, channel_id=channel['contentDisplay']['linearProvider'], _is_live=True)))
