import codecs
import threading
import time
from xml.sax.saxutils import escape

import arrow
from six.moves import queue

from slyguy import plugin, gui, userdata, inputstream, signals, settings
from slyguy.log import log
from slyguy.monitor import monitor
from slyguy.session import Session
from slyguy.util import get_system_arch

from .api import API
from .language import _
from .constants import ZA_EPG_URL, LICENSE_COOLDOWN

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    if not plugin.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(content, title=_.SERIES, tags='TV Shows'))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(content, title=_.MOVIES, tags='Movies'))
        folder.add_item(label=_(_.SPORT, _bold=True), path=plugin.url_for(content, title=_.SPORT, tags='Sport'))
        folder.add_item(label=_(_.KIDS, _bold=True), path=plugin.url_for(content, title=_.KIDS, tags='Kids'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)
        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    show_events = 2

    now = arrow.utcnow()
    channels = api.channels(events=show_events)
    for channel in channels:
        plot = u''
        count = 0

        for event in channel.get('events', []):
            start = arrow.get(event['startDateTime'])
            end   = arrow.get(event['endDateTime'])
            if (now > start and now < end) or start > now:
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), event['title'])
                count += 1

                if count == show_events+1:
                    break

        plot = plot.strip(u'\n')

        folder.add_item(
            label = _(_.CHANNEL, channel_number=channel['number'], channel_name=channel['name']),
            info = {'plot': plot or channel['description']},
            art = {'thumb': channel['channelLogoPaths'].get('XLARGE')},
            path = plugin.url_for(play_channel, id=channel['id'], _is_live=True),
            playable = True
        )

    return folder

@plugin.route()
def content(title, tags, sort='az', category=None, page=1, **kwargs):
    folder = plugin.Folder(title)

    page = int(page)
    data = api.content(tags, sort, category=category, page=page, pagesize=24)

    if category is None:
        category = ''
        for section in data['subSections']:
            if section['name'].lower() != 'filter':
                continue

            for row in section['items']:
                split = row['endpoint'].split('filter')
                if len(split) == 1:
                    category = ''
                else:
                    category = split[1].split(';')[0].lstrip('=')

                folder.add_item(
                    label = row['name'],
                    path = plugin.url_for(content, title=title, tags=tags, sort=sort, category=category, page=page),
                )

    if not folder.items:
        items = _process_rows(data['items'])
        folder.add_items(items)

        if data['total'] > ((data['pageSize'] * data['page']) + data['count']):
            folder.add_item(
                label = _(_.NEXT_PAGE, page=page+1),
                path = plugin.url_for(content, title=title, tags=tags, sort=sort, category=category, page=page+1),
                specialsort = 'bottom',
            )

    return folder

def _process_rows(rows):
    items = []

    for row in rows:
        if 'program' in row:
            item = _process_program(row['program'])
        elif 'video' in row:
            item = _process_video(row['video'])
        else:
            continue

        items.append(item)

    return items

def _get_image(images, type='thumb', size='SMALL'):
    if type == 'thumb':
        keys = ['poster', 'play-image']
    elif type == 'fanart':
        keys = ['hero', ]

    for key in keys:
        if key in images and images[key]:
            image = images[key]
            return image.get(size) or image[list(image)[-1]]

    return None

def _process_program(program):
    return plugin.Item(
        label = program['title'],
        art   = {'thumb': _get_image(program['images']), 'fanart': _get_image(program['images'], 'fanart')},
        info  = {
            'plot': program.get('synopsis'),
            'genre': program.get('genres'),
            'tvshowtitle': program['title'],
            'mediatype': 'tvshow',
        },
        path  = plugin.url_for(list_seasons, id=program['id']),
    )

def _process_video(video):
    if video.get('type') == 'Movie':
        media_type = 'movie'
    elif video.get('type') == 'Episode':
        media_type = 'episode'
    else:
        media_type = 'video'

    return plugin.Item(
        label = video['title'],
        info  = {
            'plot': video.get('synopsis'),
            'year': video.get('yearOfRelease'),
            'duration': video.get('durationInSeconds'),
            'season': video.get('seasonNumber'),
            'episode': video.get('seasonEpisode'),
            'genre': video.get('genres'),
            'dateadded': video.get('airDate'),
            'tvshowtitle': video.get('displayTitle'),
            'mediatype': media_type,
        },
        art   = {'thumb': _get_image(video['images']), 'fanart': _get_image(video['images'], 'fanart')},
        path  = plugin.url_for(play_asset, stream_url=video['videoAssets'][0]['url'], content_id=video['videoAssets'][0]['manItemId']),
        playable = True,
    )

@plugin.route()
def list_seasons(id, **kwargs):
    series = api.series(id)

    # Flatten
    if len(series['seasons']) == 1 and settings.getBool('flatten_single_season', True):
        return _episodes(series, int(series['seasons'][0]['seasonNumber']))

    folder = plugin.Folder(series['title'])

    for row in series['seasons']:
        folder.add_item(
            label = 'Season {}'.format(row['seasonNumber']),
            info  = {
                'plot': row.get('synopsis'),
                'tvshowtitle': series['title'],
                'season': row.get('seasonNumber'),
                'mediatype': 'season',
            },
            art   = {'thumb': _get_image(series['images']), 'fanart': _get_image(series['images'], 'fanart')},
            path  = plugin.url_for(episodes, series=id, season=row['seasonNumber']),
        )

    return folder

@plugin.route()
def episodes(series, season, **kwargs):
    series = api.series(series)
    return _episodes(series, int(season))

def _episodes(series, season):
    folder = plugin.Folder(series['title'], fanart= _get_image(series['images'], 'fanart'))

    for row in series['seasons']:
        if int(row['seasonNumber']) != int(season):
            continue

        has_eps = len([x for x in row['videos'] if x['seasonEpisode']])
        for video in row['videos']:
            if has_eps and not video['seasonEpisode']:
                log.debug('Skipping info video item: {}'.format(video['title']))
                continue

            item = _process_video(video)
            folder.add_items(item)

        break

    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    items = []
    for row in api.search(query):
        item = plugin.Item(
            label = row['title'],
            art   = {'thumb': row['image'].get('LARGE')},
            info  = {},
        )

        if row['editorialItemType'] == 'Program':
            item.path = plugin.url_for(list_seasons, id=row['id'])
        elif row['editorialItemType'] == 'Video':
            item.path = plugin.url_for(play_video, id=row['id'])
            item.playable = True
        else:
            continue

        items.append(item)

    return items, False

@plugin.route()
def login(**kwargs):
    if not _device_link():
        return

    _select_profile()
    gui.refresh()

def _device_link():
    timeout = 600

    with api.device_login() as login_progress:
        with gui.progress(_(_.DEVICE_LINK_STEPS, code=login_progress.code), heading=_.DEVICE_LINK) as progress:
            for i in range(timeout):
                if progress.iscanceled() or not login_progress.is_alive() or monitor.waitForAbort(1):
                    break

                progress.update(int((i / float(timeout)) * 100))

            login_progress.stop()
            return login_progress.result

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    _select_profile()
    gui.refresh()

def _select_profile():
    options = []
    values  = []
    default = -1

    for index, profile in enumerate(api.profiles()):
        values.append(profile)
        options.append(plugin.Item(label=profile['alias'], art={'thumb': profile['avatar']['uri']}))

        if profile['id'] == userdata.get('profile'):
            default = index
            userdata.set('avatar', profile['avatar']['uri'])
            userdata.set('profile', profile['alias'])

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _set_profile(profile):
    userdata.set('profile', profile['id'])
    userdata.set('profile_name', profile['alias'])
    userdata.set('avatar', profile['avatar']['uri'])
    if profile['id']:
        gui.notification(_.PROFILE_ACTIVATED, heading=profile['alias'], icon=profile['avatar']['uri'])

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('avatar')
    userdata.delete('profile')
    userdata.delete('profile_name')
    gui.refresh()

@plugin.route()
@plugin.plugin_request()
def license_request(license_url, _data, _path, _headers, **kwargs):
    resp = Session().post(license_url, data=_data, headers=_headers)
    data = resp.content

    if not resp.ok or not data:
        cooldown_left = _get_license_cooldown()
        if b'concurrent' in data and cooldown_left:
            msg = _(_.LICENSE_COOLDOWN_ERROR, cooldown_left=cooldown_left)
        else:
            try:
                msg = resp.json()['message']
            except:
                msg = data.decode('utf8')
            msg = _(_.WIDEVINE_ERROR, error=msg)

        log.error(msg)
        gui.ok(msg)
    else:
        userdata.set('last_license', int(time.time()))

    with open(_path, 'wb') as f:
        f.write(data)
    return {'url': _path, 'headers': dict(resp.headers)}

def _get_license_cooldown():
    if get_system_arch()[0] == 'Android':
        return 0

    last_license = userdata.get('last_license', 0)
    cooldown_left = int(last_license + LICENSE_COOLDOWN - time.time())
    return cooldown_left

@plugin.route()
@plugin.login_required()
def play_asset(stream_url, content_id, **kwargs):
    url, license_url, headers = api.play_asset(stream_url, content_id)
    license_url = plugin.url_for(license_request, license_url=license_url)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url),
        headers = headers,
        path = url,
    )

@plugin.route()
@plugin.login_required()
def play_video(id, **kwargs):
    url, license_url, headers = api.play_video(id)
    license_url = plugin.url_for(license_request, license_url=license_url)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url),
        headers = headers,
        path = url,
    )

@plugin.route()
@plugin.login_required()
def play_channel(id, **kwargs):
    url, license_url, headers = api.play_channel(id)
    license_url = plugin.url_for(license_request, license_url=license_url)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url, properties={'manifest_update_parameter': 'full'}),
        headers = headers,
        path = url,
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = api.channels()
    epg_url = ZA_EPG_URL

    with codecs.open(output, 'w', encoding='utf-8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(epg_url))

        for row in data:
            genres = row.get('genres', [])
            genres = ';'.join(genres) if genres else ''

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" tvg-name="{name}" group-title="{group}" tvg-logo="{logo}",{name}\n{url}'.format(
                        id=row['id'], channel=row['number'], name=row['name'], logo=row['channelLogoPaths'].get('XLARGE', ''),
                            group=genres, url=plugin.url_for(play_channel, id=row['id'], _is_live=True)))
