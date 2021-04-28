from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.log import log
from slyguy.exceptions import PluginError

from .api import API
from .language import _
from .constants import PREVIEW_LENGTH

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), _position=0)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        folder.add_item(label=_(_.CATEGORIES, _bold=True), path=plugin.url_for(categories))
        folder.add_item(label=_(_.COLLECTIONS, _bold=True), path=plugin.url_for(collections))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))
        folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(watchlist))

        if settings.getBool('sync_playback', False):
            folder.add_item(label=_(_.WATCHING, _bold=True), path=plugin.url_for(watching))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _image(row, key):
    if key in row and not row[key].lower().strip().endswith('missing.png'):
        return row[key]

    return None

def _process_media(row, in_watchlist=False):
    if settings.getBool('child_friendly', False) and not row.get('is_child_friendly', False):
        #maybe just block playback and add label, so pagination still correct
        return None

    is_published   = row.get('is_published', True)
    is_collection  = row.get('is_collection', False)
    is_free        = row.get('is_free', False)
    is_series      = row.get('is_numbered_series', False)
    duration       = row.get('duration', 0) if plugin.logged_in or is_free else PREVIEW_LENGTH

    context = []

    if plugin.logged_in:
        if in_watchlist:
            context.append((_.REMOVE_WATCHLIST, "RunPlugin({})".format(plugin.url_for(remove_watchlist, id=row['id'], title=row['title'], series=int(is_collection)))))
        else:
            context.append((_.ADD_WATCHLIST, "RunPlugin({})".format(plugin.url_for(add_watchlist, id=row['id'], title=row['title'], series=int(is_collection)))))

    if is_collection:
        path = plugin.url_for(series, id=row['id'])
    else:
        path = _get_play_path(row['id'])

    item = plugin.Item(
        label = row.get('title'),
        info  = {'plot': row['description'], 'duration': duration, 'year': row.get('year_produced')},
        art   = {'thumb': _image(row, 'image_medium')},
        path  = path,
        context = context,
        playable = not is_collection,
    )

    if settings.getBool('sync_playback', False):
        try:
            resume_from = row['user_media']['progress_in_seconds']
        except:
            resume_from = 0

        item.properties['ResumeTime'] = resume_from
        item.properties['TotalTime']  = resume_from

    return item

def _search_category(rows, id):
    for row in rows:
        if str(row['id']) == str(id):
            return row

        subcats = row.get('subcategories', [])
        if subcats:
            row = _search_category(subcats, id)
            if row:
                return row

    return None

@plugin.route()
def categories(id=None, **kwargs):
    folder = plugin.Folder(_.CATEGORIES)

    rows = api.categories()
    if id:
        row = _search_category(rows, id)
        if not row:
            raise PluginError(_(_.CATEGORY_NOT_FOUND, category_id=id))

        folder.title = row['label']
        rows = row.get('subcategories', [])

    for row in rows:
        subcategories = row.get('subcategories', [])

        if subcategories:
            path = plugin.url_for(categories, id=row['id'])
        else:
            path = plugin.url_for(media, title=row['label'], filterby='category', term=row['name'])

        folder.add_item(
            label = row['label'],
            art   = {'thumb': _image(row, 'image_url')},
            path  = path,
        )

    return folder

@plugin.route()
def media(title, filterby, term, page=1, **kwargs):
    page = int(page)

    data = api.filter_media(filterby, term, page=page)
    total_pages = int(data['paginator']['total_pages'])

    folder = plugin.Folder(title)

    for row in data['data']:
        item = _process_media(row)
        folder.add_items([item])

    if total_pages > page:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(media, title=title, filterby=filterby, term=term, page=page+1),
        )

    return folder

@plugin.route()
def collections(page=1, **kwargs):
    page = int(page)

    data = api.collections(page=page)
    total_pages = int(data['paginator']['total_pages'])

    folder = plugin.Folder(_.COLLECTIONS)

    for row in data['data']:
        folder.add_item(
            label = row['title'],
            info  = {'plot': row['description']},
            art   = {'thumb': _image(row, 'image_url')},
            path  = plugin.url_for(collection, id=row['id']),
        )

    if total_pages > page:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(collections, page=page+1),
        )

    return folder

@plugin.route()
def series(id, **kwargs):
    data   = api.series(id)
    folder = plugin.Folder(data['title'], fanart=_image(data, 'image_large'))

    for row in data.get('media', []):
        item = _process_media(row)
        folder.add_items([item])

    return folder

@plugin.route()
def collection(id, **kwargs):
    data   = api.collection(id)
    folder = plugin.Folder(data['title'], fanart=_image(data, 'background_url'))

    for row in data.get('media', []):
        item = _process_media(row)
        folder.add_items([item])

    return folder

@plugin.route()
def featured(id=None, **kwargs):
    folder = plugin.Folder(_.FEATURED)

    rows = api.sections(7)

    if id:
        for row in rows:
            if str(row['id']) == str(id):
                folder.title = row['label']
                folder.fanart = _image(row, 'background_url')

                for subrow in row.get('media', []):
                    item = _process_media(subrow)
                    folder.add_items([item])

                break

    else:
        for row in rows:
            if row['type'] == 'custom':
                path = plugin.url_for(featured, id=row['id'])
            elif row['type'] == 'playlist':
                path = plugin.url_for(collection, id=row['model_id'])
            else:
                path = plugin.url_for(media, title=row['label'], filterby=row['type'], term=row['name'])

            thumb = _image(row, 'image_url')
            if not thumb and row.get('media', []):
                thumb = _image(row['media'][0], 'image_medium')

            folder.add_item(
                label = row['label'],
                info  = {'plot': row.get('description')},
                art   = {'thumb': thumb},
                path  = path,
            )

    return folder

@plugin.route()
def search(query=None, page=1, **kwargs):
    page = int(page)

    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return
        userdata.set('search', query)

    data = api.filter_media('keyword', query, page=page)
    total_pages = int(data['paginator']['total_pages'])

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query, page=page, total_pages=total_pages))

    for row in data['data']:
        item = _process_media(row)
        folder.add_items([item])

    if total_pages > page:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(search, query=query, page=page+1),
        )

    return folder

@plugin.route()
def watchlist(page=1, **kwargs):
    page = int(page)

    folder = plugin.Folder(_.WATCHLIST)
    data   = api.filter_media('bookmarked', page=page)
    total_pages = int(data['paginator']['total_pages'])

    for row in data['data']:
        item = _process_media(row, in_watchlist=True)
        folder.add_items([item])

    if total_pages > page:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(watchlist, page=page+1),
        )

    return folder

@plugin.route()
def add_watchlist(id, title, series=0, **kwargs):
    if int(series) == 1:
        result = api.set_user_collection(id, is_bookmarked='true')
    else:
        result = api.set_user_media(id, is_bookmarked='true')
    gui.notification(title, heading=_.WATCHLIST_ADDED)
    gui.refresh()

@plugin.route()
def remove_watchlist(id, title, series=0, **kwargs):
    if int(series) == 1:
        result = api.set_user_collection(id, is_bookmarked='false')
    else:
        result = api.set_user_media(id, is_bookmarked='false')

    gui.notification(title, heading=_.WATCHLIST_REMOVED)
    gui.refresh()

@plugin.route()
def watching(page=1, **kwargs):
    page = int(page)

    folder = plugin.Folder(_.WATCHING)
    data   = api.filter_media('watching', page=page)
    total_pages = int(data['paginator']['total_pages'])

    for row in data['data']:
        item = _process_media(row)
        folder.add_items([item])

    if total_pages > page:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(watchlist, page=page+1),
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

    api.login(username=username, password=password)
    gui.refresh()

def _get_play_path(id):
    kwargs = {
        'id': id,
    }

    if settings.getBool('sync_playback', False):
        kwargs['sync'] = 1

    return plugin.url_for(play, **kwargs)

@plugin.route()
def play(id, **kwargs):
    data = api.media(id)

    item = plugin.Item(
        path = data['encodings'][0]['master_playlist_url'],
        inputstream = inputstream.MPD(),
        use_proxy = True, #required for default language
        proxy_data = {'default_language': 'English'},
    )

    for row in data.get('closed_captions', []):
        item.subtitles.append([row['file'], row['code']])

    if settings.getBool('sync_playback', False):
        item.callback = {
            'type': 'interval',
            'interval': 10,
            'callback': plugin.url_for(callback, media_id=id),
        }

    return item

@plugin.route()
@plugin.no_error_gui()
def callback(media_id, _time, *kwargs):
    api.set_user_media(media_id, progress_in_seconds=int(_time))

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()