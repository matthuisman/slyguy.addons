from kodi_six import xbmcplugin

from slyguy import plugin, gui, settings, userdata, inputstream, signals
from slyguy.log import log

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
    folder = plugin.Folder()

    if not plugin.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(series))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(movies))
        folder.add_item(label=_(_.KIDS, _bold=True), path=plugin.url_for(kids))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def series(**kwargs):
    folder = plugin.Folder(_.SERIES)
    rows = api.series()
    folder.add_items(_parse_rows(rows))
    return folder

@plugin.route()
def movies(**kwargs):
    folder = plugin.Folder(_.MOVIES)
    rows = api.movies()
    folder.add_items(_parse_rows(rows))
    return folder

@plugin.route()
def kids(**kwargs):
    folder = plugin.Folder(_.KIDS)
    rows = api.kids()
    folder.add_items(_parse_rows(rows))
    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    rows = api.search(query)
    return _parse_rows(rows), False

@plugin.route()
def seasons(series_id, **kwargs):
    data = api.seasons(series_id)
    art = _get_art(data['images'])
    rows = data['seasons']

    folder = plugin.Folder(data['title'])
    folder.add_items(_parse_seasons(rows, data['title'], art))

    return folder

@plugin.route()
def episodes(season_id, **kwargs):
    data = api.episodes(season_id)
    art = _get_art(data['images'])
    rows = data['episodes']

    folder = plugin.Folder(data['tv_series']['title'], sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])
    folder.add_items(_parse_episodes(rows, data['tv_series']['title'], data['number'], art))

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
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
@plugin.login_required()
def play_trailer(asset_id, **kwargs):
    row = api.asset(asset_id)
    videos = _get_videos(row)
    return _play_videos(videos['trailer'])

@plugin.route()
@plugin.login_required()
def play(asset_id, **kwargs):
    row = api.asset(asset_id)
    videos = _get_videos(row)
    return _play_videos(videos.get('main'))

def _play_videos(videos):
    if not videos:
        plugin.exception('No videos found')

    default_audio = settings.getEnum('audio_lang', AUDIO_LANGS)

    if len(videos) == 1:
        chosen = videos[0]
    else:
        videos = sorted(videos, key=lambda x: x['language'])

        chosen  = None
        for video in videos:
            if video['language']['iso_639_3'].lower() == default_audio:
                chosen = video
                break

        if not chosen:
            index = gui.select(_.SELECT_LANG, [x['language']['name'] for x in videos])
            if index < 0:
                return

            chosen = videos[index]

    url, license_url = api.play(chosen['id'])
    item = plugin.Item(
        inputstream = inputstream.Widevine(license_url),
        path = url,
        headers = HEADERS,
    )

    return item

def _parse_series(rows):
    items = []

    for row in rows:
        videos = _get_videos(row.get('videos', []))

        item = plugin.Item(
            label = row['title'],
            info = {
                'sorttitle': row['title'],
                'plot': row['description'],
                'tvshowtitle': row['title'],
                'mediatype': 'tvshow',
            },
            art = _get_art(row.get('images', [])),
            path = plugin.url_for(seasons, series_id=row['id']),
        )

        if videos['trailer']:
            item.info['trailer'] = plugin.url_for(play_trailer, asset_id=row['id'])

        items.append(item)

    return items

def _parse_seasons(rows, series_title, series_art):
    items = []

    for row in rows:
        item = plugin.Item(
            label = _(_.SEASON_NUMBER, season_number=row['number']),
            info = {
                'plot': row['description'],
                'tvshowtitle': series_title,
                'season': row['number'],
                'mediatype': 'season',
            },
            art = _get_art(row.get('images', []), series_art),
            path = plugin.url_for(episodes, season_id=row['id']),
        )

        items.append(item)

    return items

def _parse_episodes(rows, series_title, season, season_art):
    items = []

    for row in rows:
        videos = _get_videos(row.get('videos', []))

        item = plugin.Item(
            label = row['title'] or _(_.EPISODE_NUMBER, episode_number=row['number']),
            info = {
                'plot': row.get('description'),
                'tvshowtitle': series_title,
                'season': season,
                'episode': row['number'],
                'mediatype': 'episode',
            },
            art = _get_art(row.get('images', []), season_art),
            path = plugin.url_for(play, asset_id=row['id']),
            playable = True,
        )

        if videos['main']:
            item.info.update({
                'duration': int(videos['main'][0]['duration']),
            })
            item.video = {'height': videos['main'][0]['height'], 'width': videos['main'][0]['width'], 'codec': 'h264'}

        items.append(item)

    return items

def _parse_movies(rows):
    items = []

    for row in rows:
        videos = _get_videos(row.get('videos', []))

        item = plugin.Item(
            label = row['title'],
            info = {
                'plot': row.get('description'),
                'mediatype': 'movie',
            },
            art = _get_art(row.get('images', [])),
            path = plugin.url_for(play, asset_id=row['id']),
            playable = True,
        )

        if videos['main']:
            item.info.update({
                'duration': int(videos['main'][0]['duration']),
            })
            item.video = {'height': videos['main'][0]['height'], 'width': videos['main'][0]['width'], 'codec': 'h264'}

        if videos['trailer']:
            item.info['trailer'] = plugin.url_for(play_trailer, asset_id=row['id'])

        items.append(item)

    return items

def _parse_rows(rows):
    items = []

    for row in rows:
        if row['type'] == 'movie':
            items.extend(_parse_movies([row]))
        elif row['type'] == 'tv_series':
            items.extend(_parse_series([row]))

    return items

def _get_videos(videos):
    vids = {'main': [], 'trailer': []}

    for video in videos:
        if video['usage'] == 'main':
            vids['main'].append(video)
        elif video['usage'] == 'trailer':
            vids['trailer'].append(video)

    return vids

def _get_art(images, default_art=None, fanart=True):
    art = {}
    default_art = default_art or {}

    for image in images:
        if image['type'] == 'poster':
            if image['orientation'] == 'square' or 'thumb' not in art:
                art['thumb'] = image['link'] + '/x{}'.format(THUMB_HEIGHT)
        elif image['type'] == 'background':
            art['fanart'] = image['link'] + '/x{}'.format(FANART_HEIGHT)
        elif image['type'] == 'hero' and 'fanart' not in art:
            art['fanart'] = image['link'] + '/x{}'.format(FANART_HEIGHT)
        elif image['type'] == 'poster' and image['orientation'] == 'portrait':
            art['poster'] = image['link'] + '/x{}'.format(THUMB_HEIGHT)

    for key in default_art:
        if key not in art:
            art[key] = default_art[key]

    if fanart == False:
        art.pop('fanart', None)

    return art
