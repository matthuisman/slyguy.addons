import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_TAG
from slyguy.util import async_tasks

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

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        folder.add_item(label=_(_.VIDEOS, _bold=True), path=plugin.url_for(videos))
     #   folder.add_item(label=_(_.PODCASTS, _bold=True), path=plugin.url_for(podcasts))
        folder.add_item(label=_(_.CREATORS, _bold=True), path=plugin.url_for(creators))
        folder.add_item(label=_(_.MY_LIBRARY, _bold=True), path=plugin.url_for(my_library))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def featured(**kwargs):
    folder = plugin.Folder(_.FEATURED)

    folder.add_item(label=_.LATEST_VIDEOS, path=plugin.url_for(playlist, label=_.LATEST_VIDEOS))
    folder.add_item(label=_.FEATURED_CREATORS, path=plugin.url_for(feature, feature_type='Featured Creators'))

    for row in api.collections():
        folder.add_item(label=row['title'], path=plugin.url_for(feature, feature_type=row['title']))

    return folder

@plugin.route()
def feature(feature_type, **kwargs):
    folder = plugin.Folder(feature_type)

    creators = api.creators()
    def get_creator(content_id):
        for creator in creators:
            if creator['_id'] == content_id:
                return creator

    featured = []
    for row in api.featured(feature_type):
        featured.append(get_creator(row['content_id']))

    items = _parse_creators(featured)
    folder.add_items(items)

    return folder

@plugin.route()
def videos(**kwargs):
    folder = plugin.Folder(_.VIDEOS)

    for row in api.categories():
        folder.add_item(
            label = row['title'],
            path = plugin.url_for(playlist, label=row['title'], playlist_id=row['id']),
        )

    return folder

@plugin.route()
def creators(**kwargs):
    folder = plugin.Folder(_.CREATORS)

    items = _parse_creators(api.creators())
    folder.add_items(items)

    return folder

def _get_creator(slug):
    for creator in api.creators():
        if creator['friendly_title'] == slug:
            return creator

    return None

def _parse_creators(rows, following=False):
    items = []

    for row in rows:
        item = plugin.Item(
            label = row['title'],
            info = {'plot': row['bio']},
            art = {'thumb': row['avatar'], 'fanart': row['banner']},
            path = plugin.url_for(creator_list, slug=row['friendly_title']),
        )

        if following:
            item.context.append((_(_.UNFOLLOW_CREATOR, creator=row['title']), 'RunPlugin({})'.format(plugin.url_for(unfollow_creator, slug=row['friendly_title']))))
        else:
            item.context.append((_(_.FOLLOW_CREATOR, creator=row['title']), 'RunPlugin({})'.format(plugin.url_for(follow_creator, slug=row['friendly_title']))))

        items.append(item)

    return items

def _parse_videos(rows, creator=None, following=False):
    if creator:
        creators = False
    else:
        creators = api.creators()

    items = []
    for row in rows:
        is_live = row['is_zype_live']

        def get_creator():
            for category in row['categories']:
                if category['value']:
                    for _creator in creators:
                        if _creator['title'] == category['value'][0]:
                            return _creator

        if creators:
            creator = get_creator()

        published = arrow.get(row['published_at'])

        item = plugin.Item(
            label = row['title'],
            info = {
                'duration': row['duration'],
                'plot': _(_.VIDE_PLOT, creator=creator['title'], published=published.humanize(), description=row['short_description'] or row['description']).strip(),
                'season': row.get('season'),
                'episode': row.get('episode'),
                'tvshowtitle': creator['title'],
                'mediatype': 'episode',
            },
            art = {'thumb': row['thumbnails'][0]['url'], 'fanart': creator['banner']},
            path = plugin.url_for(play, video_id=row['_id'], _is_live=is_live),
            playable = True,
            custom = {'published': published},
        )

        if following:
            item.context.append((_(_.UNFOLLOW_CREATOR, creator=creator['title']), 'RunPlugin({})'.format(plugin.url_for(unfollow_creator, slug=creator['friendly_title']))))
        else:
            item.context.append((_(_.FOLLOW_CREATOR, creator=creator['title']), 'RunPlugin({})'.format(plugin.url_for(follow_creator, slug=creator['friendly_title']))))

        if creators:
            item.context.append((_(_.CREATOR_CHANNEL, creator=creator['title']), 'Container.Update({})'.format(plugin.url_for(creator_list, slug=creator['friendly_title']))))

        items.append(item)

    return items

@plugin.route()
def playlist(label, playlist_id=None, page=1, **kwargs):
    page = int(page)

    folder = plugin.Folder(label)

    data = api.videos(playlist_id, page=page, items_per_page=settings.getInt('page_size', 20))
    items = _parse_videos(data['response'])
    folder.add_items(items)

    if data['pagination']['pages'] > page:
        folder.add_item(
            label = _(_(_.NEXT_PAGE, page=page+1), _bold=True),
            path  = plugin.url_for(playlist, label=label, playlist_id=playlist_id, page=page+1),
        )

    return folder

@plugin.route()
def creator_list(slug, page=1, **kwargs):
    page = int(page)
    creator = _get_creator(slug)

    folder = plugin.Folder(creator['title'], fanart=creator['banner'])

    data = api.videos(creator['playlist_id'], page=page, items_per_page=settings.getInt('page_size', 20))
    items = _parse_videos(data['response'], creator=creator)
    folder.add_items(items)

    if data['pagination']['pages'] > page:
        folder.add_item(
            label = _(_(_.NEXT_PAGE, page=page+1), _bold=True),
            path  = plugin.url_for(creator_list, slug=slug, page=page+1),
        )

    return folder

@plugin.route()
def follow_creator(slug, **kwargs):
    with gui.progress(background=True, percent=90):
        creator = _get_creator(slug)
        api.follow_creator(creator['_id'])

    gui.notification(_(_.FOLLOWED_CREATOR, creator=creator['title']), icon=creator['avatar'])

@plugin.route()
def unfollow_creator(slug, **kwargs):
    with gui.progress(background=True, percent=90):
        creator = _get_creator(slug)
        api.unfollow_creator(creator['_id'])

    gui.notification(_(_.UNFOLLOWED_CREATOR, creator=creator['title']), icon=creator['avatar'])
    gui.refresh()

@plugin.route()
def my_library(**kwargs):
    folder = plugin.Folder(_.MY_LIBRARY, cacheToDisc=False, no_items_method='list')

    creators = api.creators()
    def get_creator(content_id):
        for creator in creators:
            if creator['_id'] == content_id:
                return creator

    tasks = []
    _creators = []
    for row in api.following():
        _creator = get_creator(row['channel'])
        if _creator:
            _creators.append(_creator)
            task = lambda x=_creator['playlist_id']: api.videos(x, items_per_page=settings.getInt('my_library_vids_per_creator', 10))
            tasks.append(task)

    if settings.getBool('my_library_show_creators', True):
        items = _parse_creators(_creators, following=True)
        folder.add_items(items)

    videos = []
    for result in async_tasks(tasks, workers=10):
        videos.extend(result['response'])

    items = _parse_videos(videos, following=True)
    items = sorted(items, key=lambda x: x.custom['published'], reverse=True)

    folder.add_items(items)

    return folder

@plugin.route()
def search(query=None, page=1, **kwargs):
    page = int(page)

    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    if page == 1:
        items = _parse_creators(api.creators(query=query))
        folder.add_items(items)

    data = api.videos(query=query, page=page, items_per_page=settings.getInt('page_size', 20))
    items = _parse_videos(data['response'])
    folder.add_items(items)

    if data['pagination']['pages'] > page:
        folder.add_item(
            label = _(_(_.NEXT_PAGE, page=page+1), _bold=True),
            path  = plugin.url_for(search, query=query, page=page+1),
        )

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

    api.login(username, password)
    gui.refresh()

@plugin.route()
@plugin.login_required()
def play(video_id, **kwargs):
    url, subtitles = api.play(video_id)

    item = plugin.Item(
        path = url,
        inputstream = inputstream.HLS(live=ROUTE_LIVE_TAG in kwargs),
    )

    item.proxy_data['path_subs'] = {}
    for idx, row in enumerate(subtitles):
        url = 'proxy://{}.srt'.format(row['label'])
        item.subtitles.append(url)
        item.proxy_data['path_subs'][url] = row['file']

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()