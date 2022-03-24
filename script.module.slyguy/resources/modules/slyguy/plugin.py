import sys
import re
import shutil
import random
import time
import json
from functools import wraps
from six.moves.urllib_parse import quote_plus

from kodi_six import xbmc, xbmcplugin

from . import router, gui, settings, userdata, inputstream, signals, migrate, bookmarks, mem_cache
from .constants import *
from .log import log
from .language import _
from .exceptions import Error, PluginError
from .util import set_kodi_string, get_addon, remove_file, user_country

## SHORTCUTS
url_for = router.url_for
dispatch = router.dispatch
############

def exception(msg=''):
    raise PluginError(msg)

logged_in = False

class Redirect(object):
    def __init__(self, location):
        self.location = location

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
            elif isinstance(item, Redirect):
                if _handle() > 0:
                    xbmcplugin.endOfDirectory(_handle(), succeeded=True, updateListing=True, cacheToDisc=True)

                gui.redirect(item.location)
            else:
                resolve()

        router.add(url, decorated_function)
        return decorated_function
    return lambda f: decorator(f, url)

# @plugin.plugin_middleware()
def plugin_middleware():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            kwargs['_path'] = xbmc.translatePath(kwargs['_path'])
            with open(kwargs['_path'], 'rb') as f:
                kwargs['_data'] = f.read()

            remove_file(kwargs['_path'])

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

# @plugin.plugin_request()
def plugin_request():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
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
def search():
    def decorator(f):
        @wraps(f)
        def decorated_function(query=None, new=None, remove=None, page=1, **kwargs):
            page = int(page)

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
                @pagination()
                def search(page=1, **kwargs):
                    folder = Folder(_(_.SEARCH_FOR, query=query))
                    items, more_results = f(query=query, page=page, **kwargs)
                    folder.add_items(items)
                    return folder, more_results
                return search(page, **kwargs)

        return decorated_function
    return lambda f: decorator(f)

# @plugin.pagination()
def pagination():
    def decorator(f):
        @wraps(f)
        def decorated_function(page=1, **kwargs):
            multiplier = settings.getInt('pagination_multiplier') or 1

            page = int(page)
            real_page = ((page-1)*multiplier)+1

            items = []
            for i in range(multiplier):
                folder, more_results = f(page=real_page, **kwargs)
                real_page += 1
                items.extend(folder.items)
                if not more_results:
                    break

            folder.items = items
            # if page > 1:
            #     folder.title += ' (Page {})'.format(page)

            if more_results:
                folder.add_item(
                    label = _(_.NEXT_PAGE, page=page+1),
                    path = router.add_url_args(kwargs[ROUTE_URL_TAG], page=page+1),
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
        path = settings.common_settings.get('_proxy_path')+STOP_URL
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

    log.exception(e)
    gui.exception()
    resolve()

@route('')
def _home(**kwargs):
    raise PluginError(_.PLUGIN_NO_DEFAULT_ROUTE)

@route(ROUTE_ADD_BOOKMARK)
def _add_bookmark(path, label=None, thumb=None, folder=1, playable=0, **kwargs):
    bookmarks.add(path, label, thumb, int(folder), int(playable))
    gui.notification(label, heading=_.BOOKMARK_ADDED, icon=thumb)

@route(ROUTE_DEL_BOOKMARK)
def _del_bookmark(index, **kwargs):
    if bookmarks.delete(int(index)):
        gui.refresh()
    else:
        gui.redirect(url_for(''))

@route(ROUTE_RENAME_BOOKMARK)
def _rename_bookmark(index, name, **kwargs):
    new_name = gui.input(_.RENAME_BOOKMARK, default=name)
    if not new_name or new_name == name:
        return

    bookmarks.rename(int(index), new_name)
    gui.refresh()

@route(ROUTE_MOVE_BOOKMARK)
def _move_bookmark(index, shift, **kwargs):
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
            item.context.append((_.MOVE_UP, 'RunPlugin({})'.format(url_for(ROUTE_MOVE_BOOKMARK, index=index, shift=-1))))
        if index < len(_bookmarks)-1:
            item.context.append((_.MOVE_DOWN, 'RunPlugin({})'.format(url_for(ROUTE_MOVE_BOOKMARK, index=index, shift=1))))

        item.context.append((_.RENAME_BOOKMARK, 'RunPlugin({})'.format(url_for(ROUTE_RENAME_BOOKMARK, index=index, name=row['label']))))
        item.context.append((_.DELETE_BOOKMARK, 'RunPlugin({})'.format(url_for(ROUTE_DEL_BOOKMARK, index=index))))

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

@route(ROUTE_SETUP_MERGE)
def _setup_iptv_merge(**kwargs):
    addon = get_addon(IPTV_MERGE_ID, required=True, install=True)

    plugin_url = router.url_for('setup_addon', addon_id=ADDON_ID, _addon_id=IPTV_MERGE_ID)
    xbmc.executebuiltin('RunPlugin({})'.format(plugin_url))

@route(ROUTE_MIGRATE_DONE)
def _migrate_done(old_addon_id, **kwargs):
    _close()
    migrate.migrate_done(old_addon_id)

def reboot():
    _close()
    xbmc.executebuiltin('Reboot')

@signals.on(signals.AFTER_DISPATCH)
def _close():
    signals.emit(signals.ON_CLOSE)

@route(ROUTE_SETTINGS)
def _settings(**kwargs):
    _close()
    settings.open()
    gui.refresh()

@route(ROUTE_RESET)
def _reset(**kwargs):
    if not gui.yes_no(_.PLUGIN_RESET_YES_NO):
        return

    _close()

    try:
        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":false}}}}'.format(ADDON_ID))
        shutil.rmtree(ADDON_PROFILE)
    except:
        pass

    xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":true}}}}'.format(ADDON_ID))

    gui.notification(_.PLUGIN_RESET_OK)
    signals.emit(signals.AFTER_RESET)
    gui.refresh()

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
    if not seconds or seconds < 0:
        return 0

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
    index = gui.context_menu([_.PLAY_FROM_LIVE_CONTEXT, _.PLAY_FROM_BEGINNING])
    if index == -1:
        return -1
    elif index == 0:
        return 0
    else:
        return seconds

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

        if settings.getBool('bookmarks') and self.bookmark:
            url = url_for(ROUTE_ADD_BOOKMARK, path=self.path, label=self.label, thumb=self.art.get('thumb'), folder=int(self.is_folder), playable=int(self.playable))
            self.context.append((_.ADD_BOOKMARK, 'RunPlugin({})'.format(url)))

        if not self.playable:
            self.art['thumb']  = self.art.get('thumb') or default_thumb
            self.art['fanart'] = self.art.get('fanart') or default_fanart

        quality = settings.getEnum('default_quality', QUALITY_TYPES, default=QUALITY_ASK)
        if self.path and self.playable and quality not in (QUALITY_DISABLED, QUALITY_ASK):
            url = router.add_url_args(self.path, **{QUALITY_TAG: QUALITY_ASK})
            self.context.append((_.PLAYBACK_QUALITY, 'PlayMedia({},noresume)'.format(url)))

        return super(Item, self).get_li(*args, **kwargs)

    def play(self, **kwargs):
        self.playable = True

        quality = kwargs.get(QUALITY_TAG, self.quality)
        is_live = ROUTE_LIVE_TAG in kwargs

        if quality is None:
            quality = settings.getEnum('default_quality', QUALITY_TYPES, default=QUALITY_ASK)
            if quality == QUALITY_CUSTOM:
                quality = int(settings.getFloat('max_bandwidth')*1000000)
        else:
            quality = int(quality)

        self.proxy_data['quality'] = quality

        if self.resume_from is not None and self.resume_from < 0:
            self.play_skips.append({'to': int(self.resume_from)})
            self.resume_from = 1

        li = self.get_li()
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
    def __init__(self, title=None, items=None, content='AUTO', updateListing=False, cacheToDisc=True, sort_methods=None, thumb=None, fanart=None, no_items_label=_.NO_ITEMS, no_items_method='dialog', show_news=True):
        self.title = title
        self.items = items or []
        self.content = content
        self.updateListing = updateListing
        self.cacheToDisc = cacheToDisc
        self.sort_methods = sort_methods
        self.thumb = thumb or default_thumb
        self.fanart = fanart or default_fanart
        self.no_items_label = no_items_label
        self.no_items_method = no_items_method
        self.show_news = show_news

    def display(self):
        handle = _handle()
        items = [i for i in self.items if i]

        ep_sort = True
        last_show_name = ''

        item_types = {}

        if not items and self.no_items_label:
            label = _(self.no_items_label, _label=True)

            if self.no_items_method == 'dialog':
                gui.ok(label, heading=self.title)
                return resolve()
            else:
                items.append(Item(
                    label = label,
                    is_folder = False,
                ))

        count = 0.0
        for item in items:
            if self.thumb and not item.art.get('thumb'):
                item.art['thumb'] = self.thumb

            if self.fanart and not item.art.get('fanart'):
                item.art['fanart'] = self.fanart

            if not item.specialsort:
                media_type = item.info.get('mediatype')
                show_name = item.info.get('tvshowtitle')
                if media_type != 'episode' or not show_name or (last_show_name and show_name != last_show_name):
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

        if settings.common_settings.getBool('video_folder_content', False):
            content_type = 'videos'

        # data = userdata.get('view_{}'.format(content_type))
        # if data:
        #     xbmc.executebuiltin('Container.SetViewMode({})'.format(data[0]))
        #     self.content = data[1]

        if self.content == 'AUTO':
            if content_type == 'movies':
                self.content = 'movies'
            elif content_type in ('tvshows', 'seasons'):
                self.content = 'tvshows'
            elif content_type == 'episodes':
                self.content = 'tvshows'
            else:
                self.content = 'videos'

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
        position = kwargs.pop('_position', None)
        kiosk    = kwargs.pop('_kiosk', None)

        if kiosk == False and settings.getBool('kiosk', False):
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

def process_news():
    news = settings.common_settings.get('_news')
    if not news:
        return

    try:
        news = json.loads(news)
        if news.get('show_in') and ADDON_ID.lower() not in [x.lower() for x in news['show_in'].split(',')]:
            return

        settings.common_settings.set('_news', '')

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

        if news['type'] == 'message':
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
