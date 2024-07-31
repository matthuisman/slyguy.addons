import codecs
from xml.dom.minidom import parseString

import arrow
from kodi_six import xbmcplugin
from slyguy.constants import MIDDLEWARE_PLUGIN
from slyguy import plugin, gui, userdata, signals, inputstream
from slyguy.util import pthms_to_seconds

from .api import API
from .language import _
from .settings import settings, HEADERS, EPG_URL


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
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        _ondemand(folder)
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

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
def featured(**kwargs):
    folder = plugin.Folder(_.FEATURED)

    data = api.home()

    if data['hero']:
        items = process_rows([data['hero']])
        folder.add_items(items)

    for row in data['groups']:
        folder.add_item(
            label = row['title'],
            path = plugin.url_for(group, id=row['id']),
        )

    return folder

@plugin.route()
def group(id, **kwargs):
    data = api.group(id)

    folder = plugin.Folder(data['title'])
    items = process_rows(data['content'])
    folder.add_items(items)

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
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
@plugin.search()
def search(query, page, **kwargs):
    results = api.search(query)
    return process_rows(results), False

@plugin.route()
@plugin.pagination(key='after')
def collection(id, filters=None, after=None, **kwargs):
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

        return folder, False

    items = process_rows(data['contentPage']['content'])
    folder.add_items(items)
    return folder, data['contentPage']['pageInfo']['endCursor'] if data['contentPage']['pageInfo']['hasNextPage'] else None

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
                    'tvshowtitle': row['title'],
                    'genre': [x['title'] for x in row['primaryGenres']],
                },
                art = {'thumb': row['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': row['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
                path = plugin.url_for(show, id=row['id']),
            ))

        elif row['__typename'] == 'LinearChannel':
            if 'slot' in row:
                row['slots'] = [row['slot']]

            plot = u''
            count = 0
            for slot in row.get('slots', []):
                start = arrow.get(slot['start']).to('local')
                slot['programme'] = slot['programme'] or {}

                if 'show' in slot['programme']:
                    plot += u'[{}] {}\n'.format(start.format('h:mma'), slot['programme']['show']['title'])
                elif 'title' in slot['programme']:
                    plot += u'[{}] {}\n'.format(start.format('h:mma'), slot['programme']['title'])
                else:
                    plot += u'[{}] {}\n'.format(start.format('h:mma'), 'Schedule unavailable at this time')

                count += 1
                if count == 5:
                    break

            items.append(plugin.Item(
                label = u'{:03d} | {}'.format(row['number'], row['title']),
                art = {'thumb': row['tileImage']['uri']},
                info = {
                    'plot': plot.strip('\n'),
                },
                playable = True,
                path = plugin.url_for(play_linear, asset_id=row['id'], _is_live=True),
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
                    'tvshowtitle': data['title'],
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
    data = api.channels(subscribed_only=settings.getBool('subscribed_only', True))
    items = process_rows(data)
    folder.add_items(items)
    return folder

@plugin.route()
def play_linear(asset_id, **kwargs):
    return _play(asset_id, is_linear=True, is_live=True)

@plugin.route()
def play(asset_id, **kwargs):
    return _play(asset_id, is_linear=False, is_live=False)

@plugin.route()
@plugin.plugin_request()
def mpd_request(_data, _path,  **kwargs):
    root = parseString(_data)
    mpd = root.getElementsByTagName("MPD")[0]
    #latest manifest is 15S which leads to stalls. change to 5s
    mpd.setAttribute('minimumUpdatePeriod', 'PT5S')
    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

@plugin.login_required()
def _play(asset_id, is_linear=False, is_live=False):
    url, license = api.play(asset_id, is_linear=is_linear)

    item = plugin.Item(
        path = url,
        headers = HEADERS,
        inputstream = inputstream.Widevine(
            license_key = license,
        ),
    )

    if is_live:
        item.proxy_data['middleware'] = {url: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}}
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for row in api.channels(subscribed_only=settings.getBool('subscribed_only', True)):
            f.write(u'\n#EXTINF:-1 tvg-id="sky.{id}" tvg-chno="{channel}" tvg-logo="{logo}",{name}\n{url}'.format(
                        id=row['number'], channel=row['number'], name=row['title'], logo=row['tileImage']['uri'],
                            url=plugin.url_for(play_linear, asset_id=row['id'], _is_live=True)))
