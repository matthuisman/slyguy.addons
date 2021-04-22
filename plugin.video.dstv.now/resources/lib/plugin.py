import codecs
import threading
from xml.sax.saxutils import escape

import arrow
from kodi_six import xbmcplugin, xbmc
from six.moves import queue

from slyguy import plugin, gui, userdata, inputstream, signals, settings
from slyguy.session import Session
from slyguy.log import log
from slyguy.util import gzip_extract

from .api import API
from .language import _
from .constants import DEFAULT_COUNTRY, EPG_URLS

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    if not plugin.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True),   path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        folder.add_item(label=_(_.SERIES, _bold=True),  path=plugin.url_for(content, title=_.SERIES, tags='TV Shows'))
        folder.add_item(label=_(_.MOVIES, _bold=True),  path=plugin.url_for(content, title=_.MOVIES, tags='Movies'))
        folder.add_item(label=_(_.SPORT, _bold=True),   path=plugin.url_for(content, title=_.SPORT, tags='Sport'))
        folder.add_item(label=_(_.KIDS, _bold=True),    path=plugin.url_for(content, title=_.KIDS, tags='Kids'))
        folder.add_item(label=_(_.SEARCH, _bold=True),  path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

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
            label     = _(_.CHANNEL, channel_number=channel['number'], channel_name=channel['name']),
            info      = {'plot': plot or channel['description']},
            art       = {'thumb': channel['channelLogoPaths'].get('XLARGE')},
            path      = plugin.url_for(play_channel, id=channel['id'], _is_live=True),
            playable  = True
        )

    return folder

@plugin.route()
def content(title, tags, sort='az', category=None, page=0, **kwargs):
    folder = plugin.Folder(title)

    page = int(page)
    data = api.content(tags, sort, category=category, page=page, pagesize=24)

    if page > 0:
        folder.title += ' ({})'.format(page+1)

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
                    path  = plugin.url_for(content, title=title, tags=tags, sort=sort, category=category, page=page),
                )

    if not folder.items:
        items = _process_rows(data['items'])
        folder.add_items(items)

        if data['total'] > ((data['pageSize'] * data['page']) + data['count']):
            folder.add_item(
                label = _(_.NEXT_PAGE, page=page+2, _bold=True),
                path  = plugin.url_for(content, title=title, tags=tags, sort=sort, category=category, page=page+1),
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
            'plot':  program['synopsis'],
            'genre': program['genres'],
            #'mediatype': 'tvshow',
        },
        path  = plugin.url_for(list_seasons, id=program['id']),
    )

def _process_video(video):
    return plugin.Item(
        label = video['title'],
        info  = {
            'plot':      video['synopsis'],
            'year':      video['yearOfRelease'],
            'duration':  video['durationInSeconds'],
            'season':    video['seasonNumber'],
            'episode':   video['seasonEpisode'],
            'genre':     video['genres'],
            'dateadded': video['airDate'],
            'tvshowtitle': video['displayTitle'],
            'mediatype': 'episode' if video['seasonEpisode'] else 'video', #movie
        },
        art   = {'thumb': _get_image(video['images']), 'fanart': _get_image(video['images'], 'fanart')},
        path  = plugin.url_for(play_asset, stream_url=video['videoAssets'][0]['url'], content_id=video['videoAssets'][0]['manItemId']),
        playable = True,
    )

@plugin.route()
def list_seasons(id, **kwargs):
    series = api.series(id)
    folder = plugin.Folder(series['title'])

    for row in series['seasons']:
        folder.add_item(
            label = 'Season {}'.format(row['seasonNumber']),
            info  = {'plot': row.get('synopsis', '')},
            art   = {'thumb': _get_image(series['images']), 'fanart': _get_image(series['images'], 'fanart')},
            path  = plugin.url_for(episodes, series=id, season=row['seasonNumber']),
        )

    return folder

@plugin.route()
def episodes(series, season, **kwargs):
    series = api.series(series)
    folder = plugin.Folder(series['title'], fanart= _get_image(series['images'], 'fanart'), sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])

    for row in series['seasons']:
        if int(row['seasonNumber']) != int(season):
            continue

        for video in row['videos']:
            if not video['seasonEpisode']:
                log.debug('Skipping info video item: {}'.format(video['title']))
                continue

            item = _process_video(video)
            folder.add_items(item)

        break

    return folder

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

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

        folder.add_items(item)

    return folder

@plugin.route()
def login(**kwargs):
    if not _device_link():
        return

    _select_profile()
    gui.refresh()

def _device_link():
    monitor = xbmc.Monitor()
  #  device_id, code = api.device_code()
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
    can_delete = []
    default = -1

    for index, profile in enumerate(api.profiles()):
        values.append(profile)
        options.append(plugin.Item(label=profile['alias'], art={'thumb': profile['avatar']['uri']}))

        if profile['id'] == userdata.get('profile'):
            default = index
            userdata.set('avatar', profile['avatar']['uri'])
            userdata.set('profile', profile['alias'])

        elif profile['id'] and profile['canDelete']:
            can_delete.append(profile)

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    selected = values[index]

    if selected == '_delete':
        pass
        # _delete_profile(can_delete)
    elif selected == '_add':
        pass
        # _add_profile(taken_names=[x['profileName'] for x in profiles], taken_avatars=[avatars[x] for x in avatars])
    else:
        _set_profile(selected)

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
@plugin.login_required()
def play_asset(stream_url, content_id, **kwargs):
    url, license_url, headers = api.play_asset(stream_url, content_id)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url),
        headers     = headers,
        path        = url,
    )

@plugin.route()
@plugin.login_required()
def play_video(id, **kwargs):
    url, license_url, headers = api.play_video(id)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url),
        headers     = headers,
        path        = url,
    )

@plugin.route()
@plugin.login_required()
def play_channel(id, **kwargs):
    url, license_url, headers = api.play_channel(id)

    return plugin.Item(
        inputstream = inputstream.Widevine(license_url, properties={'manifest_update_parameter': 'full'}),
        headers     = headers,
        path        = url,
    )

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = api.channels()

    with codecs.open(output, 'w', encoding='utf-8') as f:
        f.write(u'#EXTM3U\n')

        for row in data:
            genres = row.get('genres', [])
            genres = ';'.join(genres) if genres else ''

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" tvg-name="{name}" group-title="{group}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                        id=row['id'], channel=row['number'], name=row['name'], logo=row['channelLogoPaths'].get('XLARGE', ''),
                            group=genres, path=plugin.url_for(play_channel, id=row['id'], _is_live=True)))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    country = userdata.get('country', DEFAULT_COUNTRY)
    epg_url = EPG_URLS.get(country)

    if epg_url:
        try:
            Session().chunked_dl(epg_url, output)
            if epg_url.endswith('.gz'):
                gzip_extract(output)
            return True
        except Exception as e:
            log.exception(e)
            log.debug('Failed to get remote epg: {}. Fall back to scraping'.format(epg_url))

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        def process_data(id, data):
            program_count = 0
            for event in data:
                channel   = event['channelTag']
                start     = arrow.get(event['startDateTime']).to('utc')
                stop      = arrow.get(event['endDateTime']).to('utc')
                title     = event.get('title')
                subtitle  = event.get('episodeTitle')
                series    = event.get('seasonNumber')
                episode   = event.get('episodeNumber')
                desc      = event.get('longSynopsis')
                icon      = event.get('thumbnailImagePaths', {}).get('THUMB')

                icon = u'<icon src="{}"/>'.format(icon) if icon else ''
                episode = u'<episode-num system="onscreen">S{}E{}</episode-num>'.format(series, episode) if series and episode else ''
                subtitle = u'<sub-title>{}</sub-title>'.format(escape(subtitle)) if subtitle else ''

                f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{subtitle}{icon}{episode}<desc>{desc}</desc></programme>'.format(
                    id=channel, start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(title), subtitle=subtitle, episode=episode, icon=icon, desc=escape(desc)))

        ids = []
        no_events = []
        for row in api.channels():
            f.write(u'<channel id="{id}"></channel>'.format(id=row['id']))
            ids.append(row['id'])

            if not row.get('events'):
                no_events.append(row['id'])

        log.debug('{} Channels'.format(len(ids)))
        log.debug('No Events: {}'.format(no_events))

        start = arrow.now('Africa/Johannesburg')
        EPG_DAYS = settings.getInt('epg_days', 3)
        WORKERS  = 3

        queue_data   = queue.Queue()
        queue_failed = queue.Queue()
        queue_tasks  = queue.Queue()
        queue_errors = queue.Queue()

        for id in ids:
            queue_tasks.put(id)

        def xml_worker():
            while True:
                id, data = queue_data.get()
                try:
                    process_data(id, data)
                except Exception as e:
                    queue_errors.put(e)
                finally:
                    queue_data.task_done()

        def worker():
            while True:
                id = queue_tasks.get()
                try:
                    data = api.epg(id, start.shift(days=-1), start.shift(days=EPG_DAYS+1), attempts=1)
                    if not data:
                        raise Exception()

                    queue_data.put([id, data])
                except Exception as e:
                    queue_failed.put(id)
                finally:
                    queue_tasks.task_done()

        for i in range(WORKERS):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()

        thread = threading.Thread(target=xml_worker)
        thread.daemon = True
        thread.start()

        queue_tasks.join()
        queue_data.join()

        if not queue_errors.empty():
            raise Exception('Error processing data')

        while not queue_failed.empty():
            id = queue_failed.get_nowait()
            data = api.epg(id, start.shift(days=-1), start.shift(days=EPG_DAYS+1), attempts=1 if id in no_events else 10)
            if data:
                process_data(id, data)
            elif id in no_events:
                log.debug('Skipped {}: Expected 0 events'.format(id))
            else:
                raise Exception('Failed {}'.format(id))

        f.write(u'</tv>')