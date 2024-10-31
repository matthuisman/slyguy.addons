import sys
import re
import shutil
import random
import time
import json
from functools import wraps
from six.moves.urllib_parse import quote_plus

from kodi_six import xbmc, xbmcplugin

from slyguy import router, gui, settings, userdata, inputstream, signals, migrate, bookmarks, mem_cache, is_donor, log, _
from slyguy.constants import *
from slyguy.exceptions import Error, PluginError, CancelDialog
from slyguy.util import set_kodi_string, get_addon, remove_file, user_country
from slyguy.settings.types import Category


## SHORTCUTS
url_for = router.url_for
dispatch = router.dispatch
redirect = router.redirect
############

def exception(msg=''):
    raise PluginError(msg)

logged_in = False

# @plugin.no_error_gui()
def no_error_gui():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                log.exception(e)
        return decorated_function
    return lambda f: decorator(f)

# @plugin.login_required()
def login_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not logged_in:
                raise PluginError(_.PLUGIN_LOGIN_REQUIRED)

            return f(*args, **kwargs)
        return decorated_function
    return lambda f: decorator(f)


# @plugin.continue_on_error()
def continue_on_error(error_msg=None):
    def decorator(f, error_msg):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                log.exception(e)
                gui.ok(str(e), heading=error_msg)
        return decorated_function
    return lambda f: decorator(f, error_msg)


# @plugin.route()
def route(url=None):
    def decorator(f, url):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            item = f(*args, **kwargs)

            autoplay = kwargs.get(ROUTE_AUTOPLAY_TAG, None)
            autofolder = kwargs.get(ROUTE_AUTOFOLDER_TAG, None)

            if autoplay is not None and isinstance(item, Folder):
                _autoplay(item, autoplay, playable=True)
            elif autofolder is not None and isinstance(item, Folder):
                _autoplay(item, autofolder, playable=False)
            elif isinstance(item, Folder):
                item.display()
            elif isinstance(item, Item):
                item.play(**kwargs)
            else:
                resolve()

        router.add(url, decorated_function)
        return decorated_function
    return lambda f: decorator(f, url)

# @plugin.plugin_middleware()
def plugin_middleware():
    log.debug('@plugin.plugin_middleware() is deprecated. Use @plugin.plugin_request() instead')
    return plugin_request()

# @plugin.plugin_request()
def plugin_request():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if '_path' in kwargs:
                kwargs['_path'] = xbmc.translatePath(kwargs['_path'])
                with open(kwargs['_path'], 'rb') as f:
                    kwargs['_data'] = f.read()
                remove_file(kwargs['_path'])

            if '_headers' in kwargs:
                kwargs['_headers'] = json.loads(kwargs['_headers'])

            try:
                data = func(*args, **kwargs)
            except Exception as e:
                log.exception(e)
                data = None

            folder = Folder(show_news=False)
            folder.add_item(
                path = quote_plus(json.dumps(data or {})),
            )
            return folder
        return decorated_function
    return lambda func: decorator(func)

# @plugin.merge()
def merge():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = False
            try:
                require_update()
                message = f(*args, **kwargs) or ''
            except Error as e:
                log.debug(e, exc_info=True)
                message = e.message
            except Exception as e:
                log.exception(e)
                message = str(e)
            else:
                result = True

            folder = Folder(show_news=False)
            folder.add_item(
                path = quote_plus(u'{}{}'.format(int(result), message)),
            )
            return folder
        return decorated_function
    return lambda f: decorator(f)

# @plugin.search()
def search(key=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(query=None, new=None, remove=None, **kwargs):
            if remove:
                queries = userdata.get('queries', [])
                if remove in queries:
                    queries.remove(remove)
                userdata.set('queries', queries)
                gui.refresh()

            elif new:
                query = gui.input(_.SEARCH).strip()
                if not query:
                    return

                queries = userdata.get('queries', [])
                if query in queries:
                    queries.remove(query)

                queries.insert(0, query)
                queries = queries[:MAX_SEARCH_HISTORY]
                userdata.set('queries', queries)
                gui.refresh()

            elif query is None:
                folder = Folder(_.SEARCH)

                folder.add_item(
                    label = _(_.NEW_SEARCH, _bold=True),
                    path = url_for(f, new=1),
                )

                for query in userdata.get('queries', []):
                    folder.add_item(
                        label = query,
                        path = url_for(f, query=query),
                        context = ((_.REMOVE_SEARCH, 'RunPlugin({})'.format(url_for(f, remove=query))),),
                    )

                return folder

            else:
                @pagination(key=key)
                def search(**kwargs):
                    folder = Folder(_(_.SEARCH_FOR, query=query))
                    items, more_results = f(query=query, **kwargs)
                    folder.add_items(items)
                    return folder, more_results
                return search(**kwargs)

        return decorated_function
    return lambda f: decorator(f)

# @plugin.pagination()
def pagination(key=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(**kwargs):
            multiplier = settings.getInt('pagination_multiplier') or 1

            if key is None:
                page = int(kwargs.get('page', 1))
                real_page = ((page-1)*multiplier)+1
                kwargs['page'] = real_page

            items = []
            for i in range(multiplier):
                if key is None:
                    folder, more_results = f(**kwargs)
                    kwargs['page'] += 1
                else:
                    folder, key_val = f(**kwargs)
                    kwargs[key] = key_val
                    more_results = key_val

                items.extend(folder.items)
                if not more_results:
                    break

            folder.items = items

            if more_results:
                if key is None:
                    _kwargs = {'page': page+1}
                else:
                    _kwargs = {key: kwargs[key]}                    

                folder.add_item(
                    label = _(_.NEXT_PAGE),
                    path = router.add_url_args(kwargs[ROUTE_URL_TAG], **_kwargs),
                    specialsort = 'bottom',
                )

            return folder

        return decorated_function
    return lambda f: decorator(f)

def resolve():
    handle = _handle()
    if handle < 0:
        return

    if '_play=1' in sys.argv[2]:
        path = settings.get('_proxy_path')+STOP_URL
        xbmcplugin.setResolvedUrl(handle, True, Item(path=path).get_li())
    else:
        xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)

@signals.on(signals.ON_ERROR)
def _error(e):
    if not e.message:
        signals.emit(signals.ON_EXCEPTION, e)
        return

    mem_cache.empty()
    _close()

    log.debug(e, exc_info=True)
    gui.ok(e.message, heading=e.heading)
    resolve()

@signals.on(signals.ON_EXCEPTION)
def _exception(e):
    mem_cache.empty()
    _close()

    if not isinstance(e, CancelDialog):
        log.exception(e)
        gui.exception()
    else:
        log.debug(e)

    resolve()


@route('')
def _home(**kwargs):
    raise PluginError(_.PLUGIN_NO_DEFAULT_ROUTE)


@route()
def add_bookmark(path, label=None, thumb=None, folder=1, playable=0, **kwargs):
    bookmarks.add(path, label, thumb, int(folder), int(playable))
    gui.notification(label, heading=_.BOOKMARK_ADDED, icon=thumb)


@route()
def del_bookmark(index, **kwargs):
    if bookmarks.delete(int(index)):
        gui.refresh()
    else:
        gui.redirect(url_for(''))


@route()
def rename_bookmark(index, name, **kwargs):
    new_name = gui.input(_.RENAME_BOOKMARK, default=name)
    if not new_name or new_name == name:
        return

    bookmarks.rename(int(index), new_name)
    gui.refresh()


@route()
def move_bookmark(index, shift, **kwargs):
    bookmarks.move(int(index), int(shift))
    gui.refresh()


@route(ROUTE_BOOKMARKS)
def _bookmarks(**kwargs):
    folder = Folder(_.BOOKMARKS)

    _bookmarks = bookmarks.get()
    for index, row in enumerate(_bookmarks):
        item = Item(
            label = row['label'],
            path = row['path'],
            art = {'thumb': row.get('thumb')},
            is_folder = bool(row.get('folder', 1)),
            playable = bool(row.get('playable', 0)),
            bookmark = False,
        )

        if index > 0:
            item.context.append((_.MOVE_UP, 'RunPlugin({})'.format(url_for(move_bookmark, index=index, shift=-1))))
        if index < len(_bookmarks)-1:
            item.context.append((_.MOVE_DOWN, 'RunPlugin({})'.format(url_for(move_bookmark, index=index, shift=1))))

        item.context.append((_.RENAME_BOOKMARK, 'RunPlugin({})'.format(url_for(rename_bookmark, index=index, name=row['label']))))
        item.context.append((_.DELETE_BOOKMARK, 'RunPlugin({})'.format(url_for(del_bookmark, index=index))))

        folder.add_items(item)

    return folder

@route(ROUTE_IA_SETTINGS)
def _ia_settings(**kwargs):
    _close()
    inputstream.open_settings()

@route(ROUTE_IA_INSTALL)
def _ia_install(**kwargs):
    _close()
    inputstream.install_widevine(reinstall=True)

@route(ROUTE_IA_HELPER)
def _ia_helper(protocol, drm='', **kwargs):
    _close()
    result = bool(inputstream.ia_helper(protocol, drm=drm))
    log.debug('IA Helper Result: {}'.format(result))
    folder = Folder(show_news=False)
    folder.add_item(
        path = str(result),
    )
    return folder

@route(ROUTE_SETUP_MERGE)
def _setup_iptv_merge(**kwargs):
    addon = get_addon(IPTV_MERGE_ID, required=True, install=True)

    plugin_url = router.url_for('setup_addon', addon_id=ADDON_ID, _addon_id=IPTV_MERGE_ID)
    xbmc.executebuiltin('RunPlugin({})'.format(plugin_url))

@route(ROUTE_MIGRATE_DONE)
def _migrate_done(old_addon_id, **kwargs):
    _close()
    migrate.migrate_done(old_addon_id)

@route(ROUTE_SETTINGS)
def _settings(category=0, **kwargs):
    category = Category.get(int(category))
    folder = Folder(category.label, content='files')

    for subcat in category.categories:
        folder.add_item(
            label = subcat.label,
            path = url_for(_settings, category=subcat.id),
            bookmark = False,
        )

    for setting in category.settings:
        item = Item(
            label = setting.label,
            path = url_for(setting_select, id=setting.id),
            bookmark = False,
            context = ((_.RESET_TO_DEFAULT, 'RunPlugin({})'.format(url_for(setting_clear, id=setting.id))),) if setting.can_clear() else None,
            is_folder = False,            
        )

        if setting.description:
            item.info['plot'] = setting.description
            item.context.append((_.HELP, 'RunPlugin({})'.format(url_for(setting_help, id=setting.id))))
        
        folder.add_items([item])

    if any(setting.can_bulk_clear() for setting in category.settings):
        folder.add_item(
            label = _(_.RESET_ALL_SETTINGS, _bold=True),
            path = url_for(clear_settings, category=category.id),
            specialsort = 'bottom',
            is_folder = False,
            bookmark = False,
        )

    return folder


@route()
def setting_help(id, **kwargs):
    setting = settings.get_setting(id)
    gui.ok(setting.description, setting._label)


@route()
def setting_select(id, **kwargs):
    setting = settings.get_setting(id)
    if setting.on_select():
        gui.refresh()


@route()
def setting_clear(id, **kwargs):
    setting = settings.get_setting(id)
    if setting.on_clear():
        gui.refresh()


@route()
def clear_settings(category=0, **kwargs):
    category = Category.get(int(category))
    to_clear = [setting for setting in category.settings if setting.can_bulk_clear()]
    if gui.yes_no(_(_.CONFIRM_CLEAR_BULK, count=len(to_clear))) and any([setting.on_clear() for setting in to_clear]):
        gui.refresh()


def reboot():
    _close()
    xbmc.executebuiltin('Reboot')


@signals.on(signals.AFTER_DISPATCH)
def _close():
    signals.emit(signals.ON_CLOSE)
    if KODI_VERSION < 19:
        signals.emit(signals.ON_EXIT)


@route(ROUTE_CONTEXT)
def _context(**kwargs):
    raise PluginError(_.NO_CONTEXT_METHOD)


@route(ROUTE_SERVICE)
def _service(**kwargs):
    try:
        signals.emit(signals.ON_SERVICE)
    except Exception as e:
        #catch all errors so dispatch doesn't show error
        log.exception(e)

# @route()
# def views(content=None, **kwargs):
#     choices = [['Movies', 'movies'], ['Shows', 'tvshows'], ['Mixed', 'mixed'], ['Menus', 'menus']]

#     if content is None:
#         folder = Folder('View Types')

#         for choice in choices:
#             folder.add_item(
#                 label = choice[0],
#                 path = url_for(views, content=choice[1]),
#             )

#         return folder

#     if content == 'movies':
#         mediatype = 'movie'
#     elif content == 'tvshows':
#         mediatype = 'tvshow'
#     elif content == 'mixed':
#         mediatype = 'movie'
#     elif content == 'menus':
#         mediatype = 'movie'

#     folder = Folder('View Type')

#     ## Add setting to each that allows changing mediatype
#     folder.add_item(
#         label = 'Save Current View',
#         path = url_for(save_view, content=content),
#         info = {'mediatype': mediatype},
#     )

#     folder.add_item(
#         label = 'Reset View',
#         path = url_for(reset_view, content=content),
#         info = {'mediatype': mediatype},
#     )

#     return folder

# @route()
# def save_view(content, **kwargs):
#     view_id = gui.get_view_id()
#     userdata.set('view_{}'.format(content), view_id)
#     gui.notification(str(view_id))
#     gui.refresh()

# @route()
# def reset_view(content, **kwargs):
#     userdata.delete('view_{}'.format(content))
#     gui.notification('Reset')
#     gui.refresh()

def service(interval=ROUTE_SERVICE_INTERVAL):
    monitor = xbmc.Monitor()

    delay = settings.getInt('service_delay', 0) or random.randint(10, 60)
    monitor.waitForAbort(delay)

    last_run = 0
    while not monitor.abortRequested():
        if time.time() - last_run >= interval:

            try:
                signals.emit(signals.ON_SERVICE)
            except Exception as e:
                #catch all errors so dispatch doesn't show error
                log.exception(e)

            last_run = time.time()

        monitor.waitForAbort(5)

def _handle():
    try: return int(sys.argv[1])
    except: return -1

def _autoplay(folder, pattern, playable=True):
    choose = 'pick'

    if '#' in pattern:
        pattern, choose = pattern.lower().split('#')

        try:
            choose = int(choose)
        except:
            if choose != 'random':
                choose = 'pick'

    log.debug('Auto {}: "{}" item that label matches "{}"'.format('Play' if playable == True else 'Select', choose, pattern))

    matches = []
    for item in folder.items:
        if not item or item.playable != playable:
            continue

        if re.search(pattern, item.label, re.IGNORECASE):
            matches.append(item)
            log.debug('#{} Match: {}'.format(len(matches)-1, item.label))

    if not matches:
        selected = None

    elif isinstance(choose, int):
        try:
            selected = matches[choose]
        except IndexError:
            selected = None

    elif len(matches) == 1:
        selected = matches[0]

    elif choose == 'random':
        selected = random.choice(matches)

    else:
        index = gui.select(folder.title, options=matches, autoclose=10000, preselect=0, useDetails=True)
        if index < 0:
            return resolve()

        selected = matches[index]

    if not selected:
        raise PluginError(_(_.NO_AUTOPLAY_FOUND, pattern=pattern, choose=choose))

    log.debug('"{}" item selected "{}"'.format(choose, selected.label))

    return router.redirect(selected.path)

default_thumb  = ADDON_ICON
default_fanart = ADDON_FANART

def resume_from(seconds):
    if not seconds or seconds < 60:
        return None

    minutes = seconds // 60
    hours = minutes // 60
    label = _(_.RESUME_FROM, '{:02d}:{:02d}:{:02d}'.format(hours, minutes % 60, seconds % 60))

    index = gui.context_menu([label, _.PLAY_FROM_BEGINNING])
    if index == -1:
        return -1
    elif index == 0:
        return seconds
    else:
        return 0

def live_or_start(seconds=1):
    index = gui.context_menu([_.PLAY_FROM_BEGINNING, _.PLAY_FROM_LIVE_CONTEXT])
    if index == -1:
        return -1
    elif index == 0:
        return seconds
    else:
        return 0

#Plugin.Item()
class Item(gui.Item):
    def __init__(self, cache_key=None, play_next=None, callback=None, play_skips=None, geolock=None, bookmark=True, quality=None, *args, **kwargs):
        super(Item, self).__init__(self, *args, **kwargs)
        self.cache_key = cache_key
        self.play_next = dict(play_next or {})
        self.callback = dict(callback or {})
        self.play_skips = play_skips or []
        self.geolock = geolock
        self.bookmark = bookmark
        self.quality = quality

    def get_li(self, *args, **kwargs):
        # if settings.getBool('use_cache', True) and self.cache_key:
        #     url = url_for(ROUTE_CLEAR_CACHE, key=self.cache_key)
        #     self.context.append((_.PLUGIN_CONTEXT_CLEAR_CACHE, 'RunPlugin({})'.format(url)))
        if settings.getBool('bookmarks', True) and self.bookmark:
            url = url_for(add_bookmark, path=self.path, label=self.label, thumb=self.art.get('thumb'), folder=int(self.is_folder), playable=int(self.playable))
            self.context.append((_.ADD_BOOKMARK, 'RunPlugin({})'.format(url)))

        if self.no_resume is None and self.path and (ROUTE_LIVE_TAG in self.path or NO_RESUME_TAG in self.path):
            self.no_resume = True

        if self.hide_favourites is None and self.specialsort or (not self.bookmark and self.path != url_for(_bookmarks)):
            self.hide_favourites = True

        if not self.playable:
            self.art['thumb'] = self.art.get('thumb') or default_thumb
            self.art['fanart'] = self.art.get('fanart') or default_fanart

        if self.path and self.playable and is_donor():
            url = router.add_url_args(self.path, **{QUALITY_TAG: QUALITY_ASK})
            self.context.append((_.SELECT_QUALITY, 'PlayMedia({},noresume)'.format(url)))

        return super(Item, self).get_li(*args, **kwargs)

    def play(self, **kwargs):
        self.playable = True

        quality = QUALITY_SKIP
        if is_donor():
            quality = kwargs.get(QUALITY_TAG, self.quality)
            if quality is None:
                quality = settings.QUALITY_MODE.value
            else:
                quality = int(quality)
        self.proxy_data['quality'] = quality

        if self.resume_from is not None and self.resume_from < 0:
            self.play_skips.append({'to': int(self.resume_from)})
            self.resume_from = 1

        li = self.get_li(playing=True)
        handle = _handle()

        play_data = {
            'playing_file': self.path,
            'next': {'time': 0, 'next_file': None},
            'skips': self.play_skips or [],
            'callback': {'type': 'interval', 'interval': 0, 'callback': None},
        }

        if self.play_next:
            play_data['next'].update(self.play_next)
            if play_data['next']['next_file']:
                play_data['next']['next_file'] = router.add_url_args(play_data['next']['next_file'], _play=1)

        if self.callback:
            play_data['callback'].update(self.callback)

        set_kodi_string('_slyguy_play_data', json.dumps(play_data))

        if handle > 0:
            xbmcplugin.setResolvedUrl(handle, True, li)
        else:
            xbmc.Player().play(self.path, li)

#Plugin.Folder()
class Folder(object):
    def __init__(self, title=None, items=None, content='AUTO', updateListing=False, cacheToDisc=True, sort_methods=None, thumb=None, fanart=None, art=None, no_items_label=_.NO_ITEMS, no_items_method='notification', show_news=True):
        self.title = title
        self.items = items or []
        self.content = content
        self.updateListing = updateListing
        self.cacheToDisc = cacheToDisc
        self.sort_methods = sort_methods
        self.thumb = thumb or default_thumb
        self.fanart = fanart or default_fanart
        self.art = art or {}
        self.no_items_label = no_items_label
        self.no_items_method = no_items_method
        self.show_news = show_news

    def display(self):
        if self.show_news:
            require_update()

        items = [i for i in self.items if i]
        if not items and self.no_items_label:
            if self.no_items_method == 'notification':
                gui.notification(self.no_items_label, heading=self.title)
                return resolve()
            elif self.no_items_method == 'dialog':
                gui.ok(self.no_items_label, heading=self.title)
                return resolve()
            else:
                items.append(Item(
                    label = _(self.no_items_label, _label=True),
                    is_folder = False,
                ))

        video_view_menus = settings.getBool('video_view_menus', False)
        video_view_media = settings.getBool('video_view_media', False)
        menu_view_shows_seasons = settings.getBool('menu_view_shows_seasons', False)

        handle = _handle()
        count = 0.0
        item_types = {}
        ep_sort = True
        last_show_name = ''
        for item in items:
            for key in self.art:
                if self.art[key] and not item.art.get(key):
                    item.art[key] = self.art[key]

            if self.thumb and not item.art.get('thumb'):
                item.art['thumb'] = self.thumb

            if self.fanart and not item.art.get('fanart'):
                item.art['fanart'] = self.fanart

            if not item.specialsort:
                media_type = item.info.get('mediatype')
                show_name = item.info.get('tvshowtitle')

                if not media_type and item.playable:
                    item.info['mediatype'] = media_type = 'video'

                if not (item.info.get('plot') or '').strip() and not item.info.get('mediatype'):
                    item.info['plot'] = '[B][/B]'

                if media_type != 'episode' or not item.info.get('episode') or not show_name or (last_show_name and show_name != last_show_name):
                    ep_sort = False

                if not last_show_name:
                    last_show_name = show_name

                if media_type not in item_types:
                    item_types[media_type] = 0

                item_types[media_type] += 1
                count += 1

            li = item.get_li()
            xbmcplugin.addDirectoryItem(handle, item.path, li, item.is_folder)

        top_type = percent = None
        if item_types:
            top_type = sorted(item_types, key=lambda k: item_types[k], reverse=True)[0]
            percent = (item_types[top_type] / count) * 100

        content_type = 'mixed'
        if percent == 100:
            if top_type == None:
                content_type = 'menus'
            elif top_type == 'movie':
                content_type = 'movies'
            elif top_type == 'tvshow':
                content_type = 'tvshows'
            elif top_type == 'season':
                content_type = 'seasons'
            elif top_type == 'episode':
                content_type = 'episodes'
            elif top_type == 'video':
                content_type = 'videos'

        if content_type in ('tvshows', 'seasons') and menu_view_shows_seasons:
            content_type = 'menus'

        if (content_type == 'menus' and video_view_menus) or (content_type != 'menus' and video_view_media):
            content_type = 'videos'

        # data = userdata.get('view_{}'.format(content_type))
        # if data:
        #     xbmc.executebuiltin('Container.SetViewMode({})'.format(data[0]))
        #     self.content = data[1]

        if self.content == 'AUTO':
            if content_type in ('movies', 'tvshows', 'seasons', 'episodes', 'videos'):
                self.content = content_type
            elif content_type == 'mixed':
                self.content = 'movies'
            else:
                self.content = None

        if self.content: xbmcplugin.setContent(handle, self.content)
        if self.title: xbmcplugin.setPluginCategory(handle, self.title)

        if not self.sort_methods:
            self.sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_VIDEO_YEAR, xbmcplugin.SORT_METHOD_DATEADDED, xbmcplugin.SORT_METHOD_PLAYCOUNT]
            if not ep_sort:
                self.sort_methods.pop(0)

        for sort_method in self.sort_methods:
            xbmcplugin.addSortMethod(handle, sort_method)

        xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=self.updateListing, cacheToDisc=self.cacheToDisc)

        if self.show_news:
            process_news()

    def add_item(self, *args, **kwargs):
        condition = kwargs.pop('_condition', None)
        position = kwargs.pop('_position', None)
        kiosk = kwargs.pop('_kiosk', None)

        if kiosk == False and settings.getBool('kiosk', False):
            return False

        if condition is not None:
            if callable(condition):
                condition = condition()
            if not condition:
                return False

        item = Item(*args, **kwargs)

        if position == None:
            self.items.append(item)
        else:
            self.items.insert(int(position), item)

        return item

    def add_items(self, items):
        if items is None:
            return

        if isinstance(items, list):
            self.items.extend(items)
        elif isinstance(items, Item):
            self.items.append(items)
        else:
            raise Exception('add_items only accepts an Item or list of Items')


def require_update():
    updates = settings.getDict('_updates')
    if not updates:
        return

    need_updated = []
    for addon_id in REQUIRED_UPDATE:
        if addon_id in updates:
            try: addon = xbmcaddon.Addon(addon_id)
            except: continue

            cur_version = addon.getAddonInfo('version')
            if updates[addon_id][0] == cur_version and time.time() > updates[addon_id][1] + UPDATE_TIME_LIMIT:
                need_updated.append([addon_id, addon.getAddonInfo('name'), cur_version])

    if need_updated:
        log.error(_(_.UPDATES_REQUIRED, updates_required='\n'.join(['{} ({})'.format(entry[1], entry[2]) for entry in need_updated])))


def process_news():
    news = settings.getDict('_news')
    if not news:
        return

    try:
        if news.get('show_in') and ADDON_ID.lower() not in [x.lower() for x in news['show_in'].split(',')]:
            return

        settings.setDict('_news', {})

        if news.get('country'):
            valid = False
            cur_country = user_country().lower()

            for rule in [x.lower().strip() for x in news['country'].split(',')]:
                if not rule:
                    continue
                elif not rule.startswith('!') and cur_country == rule:
                    valid = True
                    break
                else:
                    valid = cur_country != rule[1:] if rule.startswith('!') else cur_country == rule

            if not valid:
                log.debug('news is only for countries: {}'.format(news['country']))
                return

        if news.get('requires') and not get_addon(news['requires'], install=False):
            log.debug('news only for users with add-on: {} '.format(news['requires']))
            return

        if news['type'] in ('message', 'donate'):
            gui.ok(news['message'], news.get('heading', _.NEWS_HEADING))

        elif news['type'] == 'addon_release':
            if get_addon(news['addon_id'], install=False):
                log.debug('addon_release {} already installed'.format(news['addon_id']))
                return

            if gui.yes_no(news['message'], news.get('heading', _.NEWS_HEADING)):
                addon = get_addon(news['addon_id'], install=True)
                if not addon:
                    return

                url = url_for('', _addon_id=news['addon_id'])
                xbmc.executebuiltin('ActivateWindow(Videos,{})'.format(url))

    except Exception as e:
        log.exception(e)
