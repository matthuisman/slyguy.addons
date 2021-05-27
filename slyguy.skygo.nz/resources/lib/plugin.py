import codecs

from kodi_six import xbmcplugin
from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.constants import ROUTE_LIVE_TAG
from slyguy.util import pthms_to_seconds

from .api import API
from .constants import *
from .language import _

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
        folder.add_item(label=_(_.LIVE_TV, _bold=True),  path=plugin.url_for(live_tv))
        _ondemand(folder)
        folder.add_item(label=_(_.SEARCH, _bold=True),  path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _ondemand(folder):
    for row in api.vod_categories():
        folder.add_item(
            label = _(row['title'], _bold=True),
            path = plugin.url_for(collection, id=row['id']),
        )

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username, password)
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    results = api.search(query)
    items = process_rows(results)
    folder.add_items(items)

    return folder

@plugin.route()
def collection(id, filters=None, page=1, after=None, **kwargs):
    page = int(page)
    data = api.collection(id, filters, after=after)
    folder = plugin.Folder(data['title'])

    if filters is None and data.get('namedFilters'):
        folder.add_item(
            label = _(_.ALL, _bold=True),
            path = plugin.url_for(collection, id=id, filters=""),
        )

        for row in data.get('namedFilters', []):
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(collection, id=id, filters=row['id']),
            )

        return folder

    items = process_rows(data['contentPage']['content'])
    folder.add_items(items)

    if data['contentPage']['pageInfo']['hasNextPage']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path = plugin.url_for(collection, id=id, filters=filters or "", page=page+1, after=data['contentPage']['pageInfo']['endCursor']),
            specialsort = 'bottom',
        )

    return folder

def process_rows(rows):
    items = []

    for row in rows:
        if row['__typename'] == 'Movie' and row['asset']:
            items.append(plugin.Item(
                label = row['title'],
                info = {
                    'duration': pthms_to_seconds(row['duration']),
                    'plot': row['synopsis'],
                    'year': row['year'],
                    'mediatype': 'movie',
                    'genre': [x['title'] for x in row['primaryGenres']],
                },
                art = {'thumb': row['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': row['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
                playable = True,
                path = plugin.url_for(play, asset_id=row['asset']['id']),
            ))

        elif row['__typename'] == 'Collection':
            items.append(plugin.Item(
                label = row['title'],
                art = {'thumb': row['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal'},
                path = plugin.url_for(collection, id=row['id']),
            ))

        elif row['__typename'] == 'Show' and row['numberOfSeasons']:
            items.append(plugin.Item(
                label = row['title'],
                info = {
                    'plot': row['synopsis'],
                    'mediatype': 'tvshow',
                    'genre': [x['title'] for x in row['primaryGenres']],
                },
                art = {'thumb': row['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': row['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
                path = plugin.url_for(show, id=row['id']),
            ))

    return items

@plugin.route()
def show(id, season=None, **kwargs):
    data = api.show(id)
    genres = [x['title'] for x in data['primaryGenres']]

    folder = plugin.Folder(data['title'])

    if len(data['seasons']) == 1 and season is None and settings.getBool('flatten_single_season', True):
        season = data['seasons'][0]['id']

    for row in data['seasons']:
        if season is None:
            folder.add_item(
                label = _(_.SEASON, number=row['number']),
                info = {
                    'plot': data['synopsis'],
                    'mediatype': 'season',
                    'genre': genres,
                },
                art = {'thumb': data['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': data['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
                path = plugin.url_for(show, id=id, season=row['id']),
            )

        elif row['id'] == season:
            folder.sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED]

            for episode in row['episodes']:
                if not episode['asset']:
                    continue

                folder.add_item(
                    label = episode['title'],
                    info = {
                        'plot': episode['synopsis'],
                        'duration': pthms_to_seconds(episode['duration']),
                        'season': row['number'],
                        'episode': episode['number'],
                        'tvshowtitle': data['title'],
                        'mediatype': 'episode',
                        'genre': genres,
                    },
                    art = {'thumb': episode['image']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': data['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
                    playable = True,
                    path = plugin.url_for(play, asset_id=episode['asset']['id']),
                )

            break

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        folder.add_item(
            label = row['title'],
            art = {'thumb': row['tileImage']['uri']},
            playable = True,
            path = plugin.url_for(play, asset_id=row['id'], _is_live=True),
        )

    return folder

@plugin.route()
@plugin.login_required()
def play(asset_id, **kwargs):
    url, license = api.play(asset_id)

    item = plugin.Item(
        path        = url,
        headers     = HEADERS,
        inputstream = inputstream.Widevine(
            license_key = license,
        ),
    )

    if kwargs.get(ROUTE_LIVE_TAG):
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in api.channels():
            f.write(u'#EXTINF:-1 tvg-id="sky.{id}" tvg-chno="{channel}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                        id=row['number'], channel=row['number'], name=row['title'], logo=row['tileImage']['uri'],
                            path=plugin.url_for(play, asset_id=row['id'], _is_live=True)))