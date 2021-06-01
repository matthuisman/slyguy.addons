import arrow
import string
import re

from kodi_six import xbmcplugin

from slyguy import plugin, settings, signals, inputstream, userdata, gui

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

    folder.add_item(label=_(_.FEATURED, _bold=True),    path=plugin.url_for(featured))
    folder.add_item(label=_(_.SHOWS, _bold=True),  path=plugin.url_for(shows))
    folder.add_item(label=_(_.CATEGORIES, _bold=True),  path=plugin.url_for(categories))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))
    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def featured(selected=None, **kwargs):
    folder = plugin.Folder(_.FEATURED if selected is None else selected)

    show_ids = []
    video_ids = []
    for row in api.featured():
        if selected and row['title'] == selected:
            if row['type'] == 'video':
                video_ids = row['items']
            else:
                show_ids = row['items']
            break

        if not selected and row['type'] in ('video', 'show'):
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(featured, selected=row['title']),
            )

    if show_ids:
        rows = [x for x in api.shows() if x['id'] in show_ids]
        items = _parse_shows(rows)
        folder.add_items(items)

    elif video_ids:
        for row in api.videos(video_ids):
            item = _parse_episode(row, use_name=True)
            folder.add_items(item)

    return folder

@plugin.route()
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    rows = []
    for row in api.shows():
        if not row['tv_show'].strip():
            continue

        if query.lower() in row['tv_show'].lower():
            rows.append(row)

    items = _parse_shows(rows)
    folder.add_items(items)

    return folder

@plugin.route()
def categories(category=None, **kwargs):
    folder = plugin.Folder(_.CATEGORIES if category is None else category)

    genres = []
    shows = []
    for row in api.shows():
        if category and row['genre'] == category:
            shows.append(row)

        elif row['genre'] and row['genre'] not in genres:
            genres.append(row['genre'])

    if shows:
        items = _parse_shows(shows)
        folder.add_items(items)
    else:
        for genre in sorted(genres):
            folder.add_item(
                label = genre,
                path = plugin.url_for(categories, category=genre),
            )

    return folder

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

    rows = []
    for row in api.shows():
        if not row['tv_show'].strip():
            continue

        sort_by = row['tv_show'].upper().strip()[0]
        if sort_by not in string.ascii_uppercase:
            sort_by = SORT_0_9

        if sort == SORT_ALL or sort == sort_by:
            rows.append(row)

    items = _parse_shows(rows)
    folder.add_items(items)

    return folder

@plugin.route()
def show(show_id, **kwargs):
    show = api.show(int(show_id))
    
    folder = plugin.Folder(show['tv_show'])

    seasons = []
    extras = None
    for row in show['seasons']:
        if 'season' in row['seasonName'].lower():
            seasons.append(row)
        elif 'extras' in row['seasonName'].lower():
            extras = row

    seasons = sorted(seasons, key=lambda x: int(x['seasonName'].replace('Season', '').strip()))
    if extras and 'extra' in show['noOfEpisodes'].lower() and not settings.getBool('hide_extras', False):
        seasons.append(extras)

    if len(seasons) == 1 and settings.getBool('flatten_single_season', True):
        return _season(show['id'], seasons[0]['seasonId'])

    for row in seasons:
        folder.add_item(
            label = row['seasonName'],
            info = {
                'plot': show['description'],
                'tvshowtitle': show['tv_show'],
                'genre': show['genre'],
                'mediatype': 'season',
            },
            art = {'thumb': show['posterArt'], 'fanart': show['tvBackgroundURL']},
            path = plugin.url_for(season, show_id=show['id'], season_id=row['seasonId']),
        )

    return folder

@plugin.route()
def season(show_id, season_id, **kwargs):
    return _season(int(show_id), int(season_id))

def _parse_episode(row, use_name=False):
    match = re.search('episode ([0-9]+)', row['customFields']['clip_title'], re.IGNORECASE)
    episode = 0 if not match else int(match.group(1))

    if use_name:
        title = row['name']
    else:
        title = row['customFields']['clip_title']
        if ',' in title:
            title = title.split(',')[1]

    return plugin.Item(
        label = title,
        info = {
            'plot': row.get('shortDescription'),
            'season': int(row['customFields']['tv_season']),
            'episode': episode,
            'tvshowtitle': row['customFields']['tv_show'],
            'mediatype': 'episode',
            'duration': int(row['length']/1000),
        },
        art = {'thumb': row['videoStillURL']},
        playable = True,
        path = plugin.url_for(play, id=row['id']),
    )

def _season(show_id, season_id):
    show, episodes = api.season(show_id, season_id)

    folder = plugin.Folder(show['tv_show'], fanart=show['tvBackgroundURL'], sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED, xbmcplugin.SORT_METHOD_UNSORTED])

    for row in episodes:
        item = _parse_episode(row)
        folder.add_items(item)

    return folder

def _parse_shows(rows):
    items = []

    for row in rows:
        item = plugin.Item(
            label = row['tv_show'],
            info = {
                'plot': row['description'] + '\n\n[B]{}[/B]'.format(row['noOfEpisodes'].split(',')[0]),
                'tvshowtitle': row['tv_show'],
                'genre': row['genre'],
                'mediatype': 'tvshow',
            },
            art = {'thumb': row['posterArt'], 'fanart': row['tvBackgroundURL']},
            path = plugin.url_for(show, show_id=row['id']),
        )

        items.append(item)

    return items

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    now = arrow.now()
    for row in api.live_channels():
        plot = u''
        count = 0

        for event in row.get('Schedule', []):
            start = arrow.get(event['ScheduleStart'])
            end = arrow.get(event['ScheduleEnd'])

            if (now > start and now < end) or start > now:
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), event['Name'])
                count += 1
                if count == 5:
                    break

        folder.add_item(
            label = row['ChannelDisplay'],
            art = {'thumb': row['ChannelLogo'].split('?')[0] + '?width=450'},
            info = {
                'plot': plot.strip('\n'),
            },
            playable = True,
            path = plugin.url_for(play_channel, id=row['Channel'], _is_live=True),
        )

    return folder

@plugin.route()
def play(id, **kwargs):
    url = api.play(id)

    return plugin.Item(
        path = url,
        headers = HEADERS,
        inputstream = inputstream.HLS(live=False),
    )

@plugin.route()
def play_channel(id, **kwargs):
    url = api.play_channel(id)

    return plugin.Item(
        path = url,
        headers = HEADERS,
        inputstream = inputstream.HLS(live=True),
    )
