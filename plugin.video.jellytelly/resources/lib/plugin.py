from kodi_six import xbmcplugin

from slyguy import plugin, gui, userdata, signals

from .api import API
from .language import _
from .settings import settings


api = API()


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in


@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder()

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_.ALL_SHOWS, path=plugin.url_for(apps, key='series_by_label', title=_.ALL_SHOWS))
        folder.add_item(label=_.POPULAR, path=plugin.url_for(apps, key='popular_series', title=_.POPULAR))
        folder.add_item(label=_.NEW_SHOWS, path=plugin.url_for(apps, key='new_episodes', title=_.NEW_SHOWS))
        folder.add_item(label=_.DEVOTIONALS, path=plugin.url_for(apps, key='devotionals', title=_.DEVOTIONALS))

        folder.add_item(label=_.WATCHLIST, path=plugin.url_for(watchlist))
        folder.add_item(label=_.FAVOURITES, path=plugin.url_for(favourites))
        folder.add_item(label=_.SEARCH, path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_.BOOKMARKS, path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
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

    api.login(username=username, password=password)
    gui.refresh()


@plugin.route()
def apps(key, title, **kwargs):
    folder = plugin.Folder(title)

    for row in api.apps(key):
        item = _parse_series(row)
        folder.add_items([item])

    return folder

@plugin.route()
def watchlist(**kwargs):
    folder = plugin.Folder(_.WATCHLIST)

    for row in api.apps('watchlist'):
        item = _parse_series(row)
        item.context = [(_.REMOVE_WATCHLIST, "RunPlugin({})".format(plugin.url_for(del_watchlist, series_id=row['id'])))]
        folder.add_items([item])

    return folder

@plugin.route()
def favourites(**kwargs):
    folder = plugin.Folder(_.FAVOURITES)

    for row in api.favourites():
        item = _parse_video(row)
        item.context = [(_.REMOVE_FAVOURITE, "RunPlugin({})".format(plugin.url_for(del_favourite, video_id=row['id'])))]
        folder.add_items([item])

    return folder

def _parse_series(row):
    return plugin.Item(
        label   = row['name'],
        info    = {'plot': row['description']},
        art     = {'thumb': row.get('images', {}).get('medium') or row.get('imageUrl')},
        path    = plugin.url_for(series, series_id=row['id']),
        context = [(_.ADD_WATCHLIST, "RunPlugin({})".format(plugin.url_for(add_watchlist, series_id=row['id'], title=row['name'])))],
    )

def _parse_video(row):
    return plugin.Item(
        label   = row['name'],
        info    = {
            'plot': row['description'],
            'duration': row.get('length'),
            'season': row.get('season'),
            'episode': row.get('episode'),
        },
        art     = {'thumb': row.get('images', {}).get('medium') or row.get('image_url')},
        path    = plugin.url_for(play, series_id=row['series_id'], video_id=row['id']),
        context = [(_.ADD_FAVOURITE, "RunPlugin({})".format(plugin.url_for(add_favourite, video_id=row['id'], title=row['name'])))],
        playable = True,
    )

@plugin.route()
def series(series_id, **kwargs):
    data = api.series(series_id)

    folder = plugin.Folder(data['name'], fanart=data.get('images', {}).get('large') or data.get('imageUrl'), sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED, xbmcplugin.SORT_METHOD_UNSORTED])

    for row in data['videos']:
        item = _parse_video(row)
        folder.add_items([item])

    return folder

@plugin.route()
@plugin.login_required()
def play(series_id, video_id, **kwargs):
    streams = api.streams(series_id, video_id)

    streams = sorted(streams, key=lambda x: (x['quality'] == 'hls', x.get('height')), reverse=True)
    selected = streams[0]

    return plugin.Item(
        path = selected['link'],
    )

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    rows  = api.search(query)
    for row in rows:
        item = _parse_series(row)
        folder.add_items([item])

    return folder

@plugin.route()
@plugin.login_required()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
def add_watchlist(series_id, title, **kwargs):
    api.add_watchlist(series_id)
    gui.notification(_(_.WATCHLIST_ADDED, title=title))

@plugin.route()
def del_watchlist(series_id, **kwargs):
    api.del_watchlist(series_id)
    gui.refresh()

@plugin.route()
def add_favourite(video_id, title, **kwargs):
    api.add_favourite(video_id)
    gui.notification(_(_.FAVOURITE_ADDED, title=title))

@plugin.route()
def del_favourite(video_id, **kwargs):
    api.del_favourite(video_id)
    gui.refresh()