import os
import string

import arrow
from kodi_six import xbmcplugin
from slyguy import plugin, gui, settings, userdata, inputstream, signals
from slyguy.constants import *
from slyguy.util import pthms_to_seconds
from slyguy.session import Session
from slyguy.router import add_url_args
from slyguy.log import log

from .api import API
from .constants import HEADERS, EPG_URL
from .language import _

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(page, title=_.FEATURED))
    folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(shows))
    folder.add_item(label=_(_.SPORT, _bold=True), path=plugin.url_for(page, slug='sport', title=_.SPORT))
    folder.add_item(label=_(_.CATEGORIES, _bold=True), path=plugin.url_for(categories))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))
    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS,  path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _process_show(data):
    label = data['title']
    if data['badge']:
        label = _(_.BADGE, label=label, badge=data['badge']['label'])

    if not data['videosAvailable'] and settings.getBool('hide_empty_shows', True):
        return None

    return plugin.Item(
        label = label,
        info = {
            'plot': data['synopsis'],
            'tvshowtitle': data['title'],
            'mediatype': 'tvshow',
        },
        art = {
            'thumb': _get_image(data['tileImage']),
            'fanart': _get_image(data['coverImage'], '?width=1920&height=548'),
        },
        path = plugin.url_for(show, slug=data['page']['href'].split('/')[-1]),
    )

def _process_video(data, showname, categories=None):
    categories = categories or []

    replaces = {
        '${video.publishedDateTime}': lambda: arrow.get(data['publishedDateTime']).format('dddd D MMM'),
        '${video.broadcastDateTime}': lambda: arrow.get(data['broadcastDateTime']).format('dddd D MMM'),
        '${video.seasonNumber}': lambda: data['seasonNumber'],
        '${video.episodeNumber}': lambda: data['episodeNumber'],
        '${video.title}': lambda: data['title'],
    }

    for key in data['labels']:
        label = data['labels'][key] or ''
        for replace in replaces:
            if replace in label:
                label = label.replace(replace, replaces[replace]())
        data['labels'][key] = label

    label = '{}'.format(data['labels']['primary'])
    if 'Movies' in categories:
        categories.remove('Movies')
        _type = 'movie'
    else:
        _type = 'episode'

    if data['labels'].get('secondary'):
        plot = '[B]{}[/B]\n\n{}'.format(data['labels']['secondary'], data['synopsis'])
    else:
        plot = data['synopsis']

    info = {'plot': plot, 'mediatype': _type, 'genre': categories, 'duration': pthms_to_seconds(data.get('duration'))}
    if _type == 'episode':
        info['tvshowtitle'] = showname
        info['season'] = data['seasonNumber']
        info['episode'] = data['episodeNumber']
        if data['title'] != showname:
            label = data['title']

    path = None
    meta = data['publisherMetadata']
    if 'brightcoveVideoId' in meta:
        path = plugin.url_for(play, brightcoveId=meta['brightcoveVideoId'])
    elif 'liveStreamUrl' in meta:
        path = plugin.url_for(play, livestream=meta['liveStreamUrl'], _is_live=meta['state'] != 'dvr')

        if meta['state'] == 'live':
            label = _(_.BADGE, label=label, badge=_.LIVE_NOW)
        elif meta['state'] == 'prepromotion':
            label = _(_.BADGE, label=label, badge=_.STARTING_SOON)
        elif meta['state'] == 'dvr':
            pass

    return plugin.Item(
        label = label,
        info = info,
        art = {'thumb': data['image']['src']+'?width=400'},
        playable = path != None,
        path = path,
    )

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
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
def page(title, slug='', **kwargs):
    sections = api.page(slug)
    folder = plugin.Folder(title)
    for row in sections:
        folder.add_item(
            label = row['name'],
            path = plugin.url_for(section, href=row['href']),
        )
    return folder

@plugin.route()
@plugin.pagination(key='href')
def section(href, **kwargs):
    data = api.section(href)
    folder = plugin.Folder(data['title'])

    for row in data.get('items', []):
        item = _parse_row(row['_embedded'])
        folder.add_items(item)

    return folder, data['nextPage']

@plugin.route()
def shows(sort=None, **kwargs):
    SORT_ALL = 'ALL'
    SORT_0_9 = '0 - 9'

    sortings = [[_(_.ALL, _bold=True), SORT_ALL], [_.ZERO_NINE, SORT_0_9]]
    for letter in string.ascii_uppercase:
        sortings.append([letter, letter])

    if sort is None:
        folder = plugin.Folder(_.SHOWS)

        for sorting in sortings:
            folder.add_item(label=sorting[0], path=plugin.url_for(shows, sort=sorting[1]))

        return folder

    if sort == SORT_ALL:
        label = _.ALL
    elif sort == SORT_0_9:
        label = _.ZERO_NINE
    else:
        label = sort

    folder = plugin.Folder(_(_.SHOWS_LETTER, sort=label))

    for section in api.a_to_z():
        if sort == None:
            folder.add_item(
                label = section['name'],
                info  = {'plot': '{} Shows'.format(len(section['items']))},
                path  = plugin.url_for(shows, sort=section['name']),
            )

        elif sort == section['name'] or sort == SORT_ALL:
            for row in section['items']:
                item = _process_show(row['_embedded'])
                folder.add_items(item)

    return folder

@plugin.route()
def category(slug, title=None, **kwargs):
    _title, shows = api.category(slug)
    folder = plugin.Folder(title or _title)

    for row in shows:
        item = _process_show(row['_embedded'])
        folder.add_items(item)

    return folder

@plugin.route()
def categories(**kwargs):
    folder = plugin.Folder(_.CATEGORIES)

    for row in api.categories():
        folder.add_item(
            label = row['_embedded']['title'],
            info = {'plot': row['_embedded']['synopsis']},
            art = {'thumb': _get_image(row['_embedded']['tileImage'])},
            path = plugin.url_for(category, slug=row['href'].split('/')[-1]),
        )

    return folder

@plugin.route()
def show(slug,  **kwargs):
    _show, sections, embedded = api.show(slug)

    categories = []
    for i in _show['categories']:
        categories.append(i['label'])

    fanart = _get_image(_show['coverImage'], '?width=1920&height=548')
    folder = plugin.Folder(_show['title'], fanart=fanart)

    count = 0
    for row in sections:
        if row['_embedded']['sectionType'] == 'similarContent':
            folder.add_item(
                label = row['label'],
                art = {'thumb': _get_image(_show['tileImage'])},
                path = plugin.url_for(similar, href=row['_embedded']['id'], label=_show['title'], fanart=fanart),
            )
        else:
            for module in row['_embedded']['layout']['slots']['main']['modules']:
                if module['type'] != 'showVideoCollection':
                    continue
            
                for _list in module['lists']:
                    count += 1
                    if count == 1 and _show['videosAvailable'] == 1 and settings.getBool('flatten_single_season', True):
                        # Try to flatten
                        try:
                            data = embedded[embedded[_list['href']]['content'][0]['href']]
                            item = _process_video(data, _show['title'], categories=categories)
                            folder.add_items(item)
                            continue
                        except:
                            pass

                    item = plugin.Item(
                        label = _list['label'] or module['label'],
                        art = {'thumb': _get_image(_show['tileImage'])},
                        path = plugin.url_for(video_list, href=_list['href'], label=_show['title'], fanart=fanart),
                    )

                    if 'season' in item.label.lower():
                        item.info['mediatype'] = 'season'
                        folder.items.insert(0, item)
                    else:
                        folder.items.append(item)

    return folder

@plugin.route()
@plugin.pagination(key='href')
def video_list(href, label, fanart, **kwargs):
    if 'sortOrder=oldestFirst' in href:
        limit = 60
        sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED]
    else:
        limit = 10
        sort_methods = [xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_EPISODE,xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED]

    folder = plugin.Folder(label, fanart=fanart, sort_methods=sort_methods)

    next_page = href
    while next_page:
        rows, next_page = api.video_list(next_page)

        for row in rows:
            item = _process_video(row['_embedded'], label)
            folder.add_items(item)
        
        if len(folder.items) == limit:
            break

    return folder, next_page

@plugin.route()
def similar(href, label, fanart, **kwargs):
    folder = plugin.Folder(label, fanart=fanart)

    for row in api.similar(href):
        item = _process_show(row['_embedded'])
        folder.add_items(item)

    return folder

def _get_image(data, params='?width=400'):
    return data['src'] + params if data else None

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    items = []
    for row in api.search(query):
        items.append(_parse_row(row))
    return items, False

def _parse_row(row):
    if row['type'] == 'show':
        return _process_show(row)
    elif row['type'] == 'category':
        slug = row['page']['href'].split('/')[-1]
        if slug == 'shows':
            slug = 'all'

        return plugin.Item(
            label = row['title'],
            info = {'plot': row['searchDescription'] or row['synopsis']},
            art = {'thumb': _get_image(row['tileImage'])},
            path = plugin.url_for(category, slug=slug),
        )
    elif row['type'] == 'channel':
        return plugin.Item(
            label = row['title'],
            info = {'plot': row['searchDescription'] or row['synopsis']},
            art = {'thumb': _get_image(row['tileImage'])},
            path = plugin.url_for(play, channel=row['page']['href'].split('/')[-1], _is_live=True),
            playable = True,
        )
    elif row['type'] == 'sportVideo':
        item = _process_sport_video(row)
        return item
    elif row['type'] == 'sport':
        slug = row['page']['href'].split('page/')[1]
        return plugin.Item(
            label = row['title'],
            info = {'plot': row['searchDescription'] or row['synopsis']},
            art = _get_sport_images(row),
            path = plugin.url_for(page, title=row['title'], slug=row['page']['href'].split('page/')[1]),
        )

def _get_sport_images(row):
    images = {}
    for img in row.get('images', []):
        if img['type'] == 'tile':
            images['thumb'] = img['src']
        elif img['type'] == 'cover':
            images['fanart'] = img['src']
    return images

def _process_sport_video(row):
    now = arrow.now()

    is_live = row['videoType'] == 'LIVE'
    title = row['title']
    if row['phase']:
        title += ' : ' + row['phase']

    start = now
    end = now
    if 'startTime' in row['media']:
        start = arrow.get(row['media']['startTime'])
    if 'endTime' in row['media']:
        end = arrow.get(row['media']['endTime'])

    if row['media']['source'] == 'brightcove':
        path = plugin.url_for(play, brightcoveId=row['media']['id'], _is_live=is_live)
    else:
        path = plugin.url_for(play, mediakindhref=row['playbackHref'], _is_live=is_live)

    item = plugin.Item(
        label = title,
        info = {'plot': row['description'] or row['synopsis'], 'duration': pthms_to_seconds(row['media']['duration'])},
        art = _get_sport_images(row),
        path = path,
        playable = True,
    )

    if start < now and end > now:
        item.label += _(' (LIVE)', _bold=True)
        item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
            add_url_args(path, play_type=PLAY_FROM_LIVE)
        )))

        item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
            add_url_args(path, play_type=PLAY_FROM_START)
        )))
    elif start > now:
        item.label += _(start.to('local').format(_.DATE_FORMAT), _bold=True)

    return item


@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    try:
        data = Session().gz_json(EPG_URL)
        channel_map = {
            'tvnz-1': 'mjh-tvnz-1',
            'tvnz-2': 'mjh-tvnz-2',
            'tvnz-duke': 'mjh-tvnz-duke',
        }
    except Exception as e:
        log.exception(e)
        log.debug('failed to get epg data')
        channel_map = {}

    now = arrow.now()
    epg_count = 5

    for row in api.channels():
        slug = row['href'].split('/')[-1]

        plot = u''
        count = 0
        if epg_count and slug in channel_map and channel_map[slug] in data:
            channel = data[channel_map[slug]]

            for index, program in enumerate(channel.get('programs', [])):
                start = arrow.get(program[0])
                try: stop = arrow.get(channel['programs'][index+1][0])
                except: stop = start.shift(hours=1)

                if (now > start and now < stop) or start > now:
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), program[1])
                    count += 1
                    if count == epg_count:
                        break

        if not plot:
            plot = row['_embedded']['synopsis']

        folder.add_item(
            label = row['_embedded']['title'],
            info = {'plot': plot},
            art = {'thumb': _get_image(row['_embedded']['tileImage'])},
            playable = True,
            path = plugin.url_for(play, channel=slug, _is_live=True),
        )

    return folder


@plugin.route()
def play(livestream=None, brightcoveId=None, channel=None, mediakindhref=None, play_type=None, **kwargs):
    headers = HEADERS

    if play_type is None:
        play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, PLAY_FROM_ASK)
    play_type = int(play_type)

    if channel:
        data = api.channel(channel)
        mediakindhref = data['playbackHref']

    if brightcoveId:
        item = api.get_brightcove_src(brightcoveId)

    elif livestream:
        item = plugin.Item(path=livestream, art=False, inputstream=inputstream.HLS(live=True))

        if ROUTE_LIVE_TAG in kwargs:
            if play_type == PLAY_FROM_START:
                item.resume_from = 1
            elif play_type == PLAY_FROM_ASK:
                item.resume_from = plugin.live_or_start()
                if item.resume_from == -1:
                    return

            if item.resume_from == 1:
                item.inputstream = inputstream.HLS(force=True, live=True)
                if not item.inputstream.check():
                    plugin.exception(_.LIVE_HLS_REQUIRED)

    elif mediakindhref:
        data = api.play(mediakindhref)
        if 'message' in data:
            plugin.exception(data['message'])

        item = plugin.Item(
            path = data['streaming']['dash']['url'],
            inputstream = inputstream.Widevine(license_key=data['encryption']['licenseServers']['widevine']),
        )
        headers['Authorization'] = data['encryption']['drmToken']

        if ROUTE_LIVE_TAG in kwargs:
            if not channel:
                if play_type == PLAY_FROM_START:
                    item.resume_from = 1
                elif play_type == PLAY_FROM_ASK:
                    item.resume_from = plugin.live_or_start()
                    if item.resume_from == -1:
                        return

            if not item.resume_from:
                ## Need below to seek to live over multi-periods
                item.resume_from = LIVE_HEAD

    else:
        plugin.exception('Unknown playback url')

    item.headers = headers
    return item
