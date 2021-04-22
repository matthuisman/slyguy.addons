import string

from kodi_six import xbmcplugin

from slyguy import plugin, gui, settings, userdata, inputstream

from .api import API
from .constants import EPISODE_EXPIRY
from .language import _

api = API()

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    folder.add_item(label=_(_.SHOWS, _bold=True),  path=plugin.url_for(shows))
    folder.add_item(label=_(_.GENRE, _bold=True),  path=plugin.url_for(genres))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))
    folder.add_item(label=_(_.LIVE, _bold=True),   path=plugin.url_for(live))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS,  path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

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
        if not row['name'].strip():
            continue

        sort_by = row['name'].upper().strip()[0]
        if sort_by not in string.ascii_uppercase:
            sort_by = SORT_0_9

        if sort == SORT_ALL or sort == sort_by:
            rows.append(row)

    items = _parse_shows(rows)
    folder.add_items(items)

    return folder

@plugin.route()
def genres(**kwargs):
    folder = plugin.Folder(_.GENRE)

    for row in api.genres():
        folder.add_item(
            label = row['displayName'],
            path  = plugin.url_for(genre, genre=row['slug'], title=row['displayName']),
            art   = {'thumb': row.get('logo', None)},
        )

    return folder

@plugin.route()
def genre(genre, title, **kwargs):
    folder = plugin.Folder(title)
    items = _parse_shows(api.genre(genre))
    folder.add_items(items)
    return folder

def _parse_shows(rows):
    items = []
    for row in rows:
        thumb = row.get('images',{}).get('showTile','').replace('[width]', '301').replace('[height]', '227')
        fanart = row.get('images',{}).get('dashboardHero','').replace('[width]', '1600').replace('[height]', '520')

        item = plugin.Item(
            label = row['name'],
            art   = {'thumb': thumb, 'fanart': fanart},
            path  = plugin.url_for(show, id=row['showId']),
            info = {
                'title': row['name'],
                'plot': row.get('synopsis'), 
               # 'mediatype': 'tvshow',
                'tvshowtitle': row['name'],
            }
        )

        items.append(item)

    return items

def _parse_episodes(rows):
    items = []
    for row in rows:
        videoid = row['videoRenditions']['videoCloud']['brightcoveId']
        thumb   = row.get('images',{}).get('videoTile','').split('?')[0]

        info = {
            'title': row['name'],
            'genre': row.get('genre'), 
            'plot': row.get('synopsis'), 
            'duration': int(row.get('duration')), 
            'aired': row.get('airedDate'),
            'dateadded': row.get('airedDate'),
            'mediatype': 'episode',
            'tvshowtitle': row.get('showTitle'),
        }

        try:
            info.update({
                'episode': int(row.get('episode')), 
                'season': int(row.get('season')),
            })
        except:
            pass

        item = plugin.Item(
            label = row['name'],
            art   = {'thumb': thumb},
            path  = plugin.url_for(play, id=videoid),
            info  = info,
            playable = True,
        )

        items.append(item)

    return items

@plugin.route()
def show(id, **kwargs):
    row = api.show(id)
    fanart = row.get('images',{}).get('dashboardHero','').replace('[width]', '1600').replace('[height]', '520')
    folder = plugin.Folder(row['name'], sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED, xbmcplugin.SORT_METHOD_UNSORTED], fanart=fanart)
    folder.add_items(_parse_episodes(row['episodes']))
    return folder

@plugin.route()
def play(id, **kwargs):
    return api.get_brightcove_src(id)

@plugin.route()
def play_channel(channel, **kwargs):
    for row in api.live():
        if row['title'] == channel:
            return plugin.Item(
                inputstream = inputstream.HLS(live=True), 
                path = row['videoRenditions']['videoCloud']['hlsUrl'], 
                art = False,
            )

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))
    items = _parse_shows(api.search(query))
    folder.add_items(items)

    return folder

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE)

    for row in api.live():
        folder.add_item(
            label = row['displayName'],
            art   = {'thumb': row.get('logo','').split('?')[0]},
            path  = plugin.url_for(play_channel, channel=row['title'], _is_live=True),
            playable = True,
        )

    return folder