import os

from kodi_six import xbmcvfs
from six.moves.urllib_parse import urlparse

from slyguy import plugin, gui
from slyguy.constants import ROUTE_CONTEXT, ROUTE_SETTINGS, KODI_VERSION, ADDON_ID
from slyguy.log import log
from slyguy.util import get_addon, kodi_rpc

from .settings import settings
from .youtube import play_youtube, get_youtube_id
from .mdblist import API
from .imdb import play_imdb
from .language import _

mdblist_api = API()


@plugin.route('/')
def home(**kwargs):
    video_id = get_youtube_id(kwargs['_url'])
    if video_id:
        return plugin.url_for(play_yt, video_id=video_id)
    else:
        return plugin.url_for(ROUTE_SETTINGS)


def _get_trailer_path(path):
    if not path:
        return ''

    video_id = get_youtube_id(path)
    if video_id:
        return plugin.url_for(play_yt, video_id=video_id)
    else:
        return path


def _li_to_item(li):
    vid_tag = li.getVideoInfoTag()

    item = plugin.Item()
    item.label = u"{} ({})".format(li.getLabel(), _.TRAILER)
    item.info = {
        'title': li.getLabel(),
        'plot': vid_tag.getPlot(),
        'tagline': vid_tag.getTagLine(),
        'trailer': vid_tag.getTrailer(),
        'year': vid_tag.getYear(),
        'mediatype': vid_tag.getMediaType(),
        'dir': None,
        'filename': None,
        'unique_id': {},
    }

    if item.info['mediatype'] == 'movie':
        path = vid_tag.getFilenameAndPath()
        item.info['dir'] = os.path.dirname(path)
        item.info['filename'] = os.path.basename(path)
    elif item.info['mediatype'] == 'tvshow':
        item.info['dir'] = os.path.dirname(vid_tag.getPath())

    for key in ['thumb','poster','banner','fanart','clearart','clearlogo','landscape','icon']:
        item.art[key] = li.getArt(key)

    if KODI_VERSION >= 20:
        item.info['genre'] = vid_tag.getGenres()
        for id_type in ('imdb', 'tvdb', 'tmdb'):
            unique_id = vid_tag.getUniqueID(id_type)
            if unique_id:
                item.info['unique_id'] = {'type': id_type, 'id': unique_id}
                break
    else:
        item.info['genre'] = vid_tag.getGenre()
        item.info['unique_id'] = {'type': None, 'id': vid_tag.getIMDBNumber()}

    return item


def _find_content_from_trailer(trailer):
    trailer = trailer.lower()
    if not trailer:
        return []

    if KODI_VERSION >= 22:
        # https://github.com/xbmc/xbmc/pull/26718
        results = kodi_rpc('VideoLibrary.GetMovies', {'filter': {'field': 'trailer', 'operator': 'contains', 'value': [trailer]},
                                                      'properties': ['title', 'year', 'imdbnumber', 'uniqueid', 'file', 'trailer']})['movies']
        if not results:
            results = kodi_rpc('VideoLibrary.GetTvShows', {'filter': {'field': 'trailer', 'operator': 'contains', 'value': [trailer]},
                                                           'properties': ['title', 'year', 'imdbnumber', 'uniqueid', 'file', 'trailer']})['tvshows']
        return results
    else:
        results = []
        rows = kodi_rpc('VideoLibrary.GetMovies', {'filter': {'field': 'hastrailer', 'operator': 'true', 'value': '1'}, 'properties': ['trailer']})['movies']
        for row in rows:
            if trailer in row["trailer"].lower():
                results.append(kodi_rpc('VideoLibrary.GetMovieDetails', {'movieid': row['movieid'], 'properties': ['title', 'year', 'imdbnumber', 'uniqueid', 'file', 'trailer']})['moviedetails'])
        # shows not supported before Kodi 22
        return results


def _get_local_trailer(item):
    if item.info['mediatype'] == 'movie' and item.info['filename'] and settings.TRAILER_LOCAL.value:
        filename = os.path.splitext(item.info['filename'])[0].lower()
        files = xbmcvfs.listdir(item.info['dir'])[1]
        for file in files:
            name, ext = os.path.splitext(file.lower())
            if name in ('movie-trailer', "{}-trailer".format(filename)):
                item.path = os.path.join(item.info['dir'], file)
                if ext == '.txt':
                    with xbmcvfs.File(item.path) as f:
                        item.path = _get_trailer_path(f.read().strip())
                return

    elif item.info['mediatype'] == 'tvshow' and item.info['dir'] and settings.TRAILER_LOCAL.value:
        folder_name = os.path.basename(item.info['dir']).lower()
        files = xbmcvfs.listdir(item.info['dir'])[1]
        for file in files:
            name, ext = os.path.splitext(file.lower())
            if name in ('tvshow-trailer', "{}-trailer".format(folder_name)):
                item.path = os.path.join(item.info['dir'], file)
                if ext == '.txt':
                    with xbmcvfs.File(item.path) as f:
                        item.path = _get_trailer_path(f.read().strip())
                return


def _get_imdb_trailer(item):
    if not settings.TRAILER_IMDB.value:
        return

    media_type = item.info['mediatype']
    id = item.info['unique_id'].get('id')
    id_type = item.info['unique_id'].get('type')
    if not id or media_type == 'tvshow' and not settings.TRAILER_IMDB_TV.value:
        return

    if id_type != 'imdb':
        try:
            imdb_id = mdblist_api.get_media(media_type, id, id_type)['ids']['imdb']
        except KeyError:
            return
    else:
        imdb_id = id

    item.path = plugin.url_for(imdb, video_id=imdb_id)


@plugin.route(ROUTE_CONTEXT)
def context_trailer(listitem, **kwargs):
    item = _li_to_item(listitem)

    _get_local_trailer(item)
    if item.path:
        return item

    _get_imdb_trailer(item)
    if item.path:
        return item

    item.path = _get_trailer_path(item.info['trailer'])

    if not item.path and settings.MDBLIST.value:
        item.path = _unique_id_mdblist_trailer(
            media_type = item.info['mediatype'],
            id = item.info['unique_id'].get('id'),
            id_type = item.info['unique_id'].get('type'),
        )
        if not item.path and settings.MDBLIST_SEARCH.value:
            item.path = _search_mdblist_trailer(
                media_type = item.info['mediatype'],
                title = item.info['title'],
                year = item.info['year'],
            )

    if not item.path:
        gui.notification(_.TRAILER_NOT_FOUND)
        return

    parsed = urlparse(item.path)
    if parsed.scheme.lower() == 'plugin':
        get_addon(parsed.netloc, install=True, required=True)

    return item


def _search_mdblist_trailer(media_type, title, year):
    if not media_type or not title or not year:
        return

    results = mdblist_api.search_media(media_type, title, year, limit=1)
    if not results:
        return

    log.info("mdblist search result: {}".format(results[0]))
    if not results[0].get('ids'):
        return

    unique_id = {}
    for id_type in ('imdb', 'tvdb', 'tmdb'):
        id = results[0]['ids'].get(id_type) or results[0]['ids'].get(id_type+'id')
        if id:
            unique_id = {'type': id_type, 'id': id}
            break

    # TODO: Could play IMDB trailer
    # if uniqe_id.get('type') == 'imdb':
    return _unique_id_mdblist_trailer(media_type, unique_id['id'], id_type=unique_id['type'])


def _unique_id_mdblist_trailer(media_type, id, id_type=None):
    if not media_type or not id:
        return

    data = mdblist_api.get_media(media_type, id, id_type=id_type)
    trailer = _get_trailer_path(data.get('trailer'))
    if ADDON_ID in trailer:
        log.info("mdblist trailer: {}".format(trailer))
        return trailer


@plugin.route('/by_unique_id')
def by_unique_id(media_type, id, id_type=None, force=0, **kwargs):
    force = int(force)
    if force or settings.MDBLIST.value:
        with gui.busy():
            trailer = _unique_id_mdblist_trailer(media_type, id, id_type)
            if trailer:
                return play_youtube(get_youtube_id(trailer))
    gui.notification(_.TRAILER_NOT_FOUND)


@plugin.route('/by_title_year')
def by_title_year(media_type, title, year, force=0, **kwargs):
    force = int(force)
    if force or (settings.MDBLIST.value and settings.MDBLIST_SEARCH.value):
        with gui.busy():
            trailer = _search_mdblist_trailer(media_type, title, year)
            if trailer:
                return play_youtube(get_youtube_id(trailer))
    gui.notification(_.TRAILER_NOT_FOUND)


@plugin.route('/play')
def play_yt(video_id, **kwargs):
    with gui.busy():
        return play_youtube(video_id)


@plugin.route('/imdb')
def imdb(video_id, **kwargs):
    with gui.busy():
        return play_imdb(video_id)


# stub out search so tmdbhelper works
@plugin.route('/search')
@plugin.route('/kodion/search/query')
def search(**kwargs):
    log.warning("SlyGuy Trailers does not support Youtube search ({}). Returning empty result".format(kwargs['_url']))
    return plugin.Folder(no_items_label=None, show_news=False)


@plugin.route('/test_streams')
def test_streams(**kwargs):
    STREAMS = [
        ['YouTube 4K', plugin.url_for(play_yt, video_id='Q82tQJyJwgk')],
        ['YouTube 4K HDR', plugin.url_for(play_yt, video_id='tO01J-M3g0U')],
        ['IMDB', plugin.url_for(imdb, video_id='tt10548174')],
        ['Show tvdb id -> mdblist -> YouTube', plugin.url_for(by_unique_id, media_type='tvshow', id='392256', id_type='tvdb', force=1)],
        ['Movie imdb id -> mdblist -> YouTube', plugin.url_for(by_unique_id, media_type='movie', id='tt0133093', id_type='imdb', force=1)],
        ['Show Title / Year -> mdblist -> YouTube', plugin.url_for(by_title_year, media_type='tvshow', title='The Last of Us', year='2023', force=1)],
        ['Movie Title / Year -> mdblist -> YouTube', plugin.url_for(by_title_year, media_type='movie', title='The Matrix', year='1999', force=1)],
    ]

    folder = plugin.Folder(_.TEST_STREAMS, content=None)
    for stream in STREAMS:
        folder.add_item(label=stream[0], is_folder=False, path=stream[1])
    return folder
