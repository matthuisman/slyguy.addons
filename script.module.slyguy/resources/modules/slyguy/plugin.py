import sys
import re
import shutil
import random
import time
import json
from functools import wraps
from six.moves.urllib_parse import quote_plus

from kodi_six import xbmc, xbmcplugin
from six.moves.urllib.parse import quote

from . import router, gui, settings, userdata, inputstream, signals, migrate, bookmarks
from .constants import *
from .log import log
from .language import _
from .exceptions import Error, PluginError, FailedPlayback
from .util import set_kodi_string, get_addon, get_kodi_string, remove_file

## SHORTCUTS
url_for         = router.url_for
dispatch        = router.dispatch
############

def exception(msg=''):
    raise PluginError(msg)

logged_in = False

class Redirect(object):
    def __init__(self, location):
        self.location = location

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

# @plugin.plugin_callback()
def plugin_callback():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            with open(kwargs['_data_path'], 'rb') as f:
                kwargs['_data'] = f.read()

            remove_file(kwargs['_data_path'])

            try:
                path = func(*args, **kwargs)
            except Exception as e:
                log.exception(e)
                path = None

            folder = Folder()
            folder.add_item(
                path = quote_plus(path or ''),
            )

            return folder
        return decorated_function
    return lambda func: decorator(func)

# @plugin.route()
def route(url=None):
    def decorator(f, url):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            item = f(*args, **kwargs)

            pattern = kwargs.get(ROUTE_AUTOPLAY_TAG, None)

            if pattern is not None and isinstance(item, Folder):
                _autoplay(item, pattern)
            elif isinstance(item, Folder):
                item.display()
            elif isinstance(item, Item):
                item.play(quality=kwargs.get(QUALITY_TAG))
            elif isinstance(item, Redirect):
                if _handle() > 0:
                    xbmcplugin.endOfDirectory(_handle(), succeeded=True, updateListing=True, cacheToDisc=True)

                gui.redirect(item.location)
            else:
                resolve()

        router.add(url, decorated_function)
        return decorated_function
    return lambda f: decorator(f, url)

# @plugin.merge()
def merge():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            folder = Folder()

            try:
                f(*args, **kwargs)
            except Error as e:
                log.debug(e, exc_info=True)
                message = e.message
            except Exception as e:
                log.exception(e)
                message = str(e)
            else:
                message = 'ok'

            folder.add_item(
                path = quote(message),
            )

            return folder

        return decorated_function
    return lambda f: decorator(f)

def resolve(error=False):
    handle = _handle()
    if handle > 0:
        if error and '_play=1' in sys.argv[2]:
            _failed_playback()
        else:
            xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)

@signals.on(signals.ON_ERROR)
def _error(e):
    if not e.message:
        signals.emit(signals.ON_EXCEPTION, e)
        return

    _close()

    log.debug(e, exc_info=True)
    gui.ok(e.message, heading=e.heading)
    resolve(error=True)

@signals.on(signals.ON_EXCEPTION)
def _exception(e):
    _close()

    if type(e) == FailedPlayback:
        _failed_playback()
        return

    log.exception(e)
    gui.exception()
    resolve(error=True)

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
    try:
        return int(sys.argv[1])
    except:
        return -1

def _autoplay(folder, pattern):
    choose = 'pick'

    if '#' in pattern:
        pattern, choose = pattern.lower().split('#')

        try:
            choose = int(choose)
        except:
            if choose != 'random':
                choose = 'pick'

    log.debug('Auto Play: "{}" item that label matches "{}"'.format(choose, pattern))

    matches = []
    for item in folder.items:
        if not item or not item.playable:
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

def _failed_playback():
    handle = _handle()
    xbmcplugin.setResolvedUrl(handle, False, Item(path='http://').get_li())
    xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=False)
    # xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
    # xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()

default_thumb  = ADDON_ICON
default_fanart = ADDON_FANART

#Plugin.Item()
class Item(gui.Item):
    def __init__(self, cache_key=None, play_next=None, callback=None, geolock=None, bookmark=True, *args, **kwargs):
        super(Item, self).__init__(self, *args, **kwargs)
        self.cache_key = cache_key
        self.play_next = dict(play_next or {})
        self.callback  = dict(callback or {})
        self.geolock   = geolock
        self.bookmark  = bookmark

    def get_li(self):
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

        return super(Item, self).get_li()

    def play(self, quality=None):
        self.playable = True

        try:
            if not self.properties.get('ForceResume', False) and sys.argv[3] == 'resume:true':
                self.properties.pop('ResumeTime', None)
                self.properties.pop('TotalTime', None)
        except:
            pass

        if quality is None:
            quality = settings.getEnum('default_quality', QUALITY_TYPES, default=QUALITY_ASK)
            if quality == QUALITY_CUSTOM:
                quality = int(settings.getFloat('max_bandwidth')*1000000)
        else:
            quality = int(quality)

        self.proxy_data['quality'] = quality

        li     = self.get_li()
        handle = _handle()

        if self.play_next:
            data = {'playing_file': self.path, 'time': 0, 'next_file': None, 'show_dialog': True}
            data.update(self.play_next)

            if data['next_file']:
                data['next_file'] = router.add_url_args(data['next_file'], _play=1)

            set_kodi_string('_slyguy_play_next', json.dumps(data))

        if self.callback:
            data = {'type': 'interval', 'playing_file': self.path, 'interval': 0, 'callback': None}
            data.update(self.callback)
            set_kodi_string('_slyguy_play_callback', json.dumps(data))

        if handle > 0:
            xbmcplugin.setResolvedUrl(handle, True, li)
        else:
            xbmc.Player().play(self.path, li)

#Plugin.Folder()
class Folder(object):
    def __init__(self, title=None, items=None, content='videos', updateListing=False, cacheToDisc=True, sort_methods=None, thumb=None, fanart=None, no_items_label=_.NO_ITEMS, no_items_method='dialog'):
        self.title = title
        self.items = items or []
        self.content = content
        self.updateListing = updateListing
        self.cacheToDisc = cacheToDisc
        self.sort_methods = sort_methods or [xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL]
        self.thumb = thumb or default_thumb
        self.fanart = fanart or default_fanart
        self.no_items_label = no_items_label
        self.no_items_method = no_items_method

    def display(self):
        handle = _handle()
        items  = [i for i in self.items if i]

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

        for item in items:
            if self.thumb and not item.art.get('thumb'):
                item.art['thumb'] = self.thumb

            if self.fanart and not item.art.get('fanart'):
                item.art['fanart'] = self.fanart

            li = item.get_li()
            xbmcplugin.addDirectoryItem(handle, item.path, li, item.is_folder)

        if self.content: xbmcplugin.setContent(handle, self.content)
        if self.title: xbmcplugin.setPluginCategory(handle, self.title)

        for sort_method in self.sort_methods:
            xbmcplugin.addSortMethod(handle, sort_method)

        xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=self.updateListing, cacheToDisc=self.cacheToDisc)

        common_data = userdata.Userdata(COMMON_ADDON)
        plugin_msg  = common_data.get('_next_plugin_msg')
        if plugin_msg:
            common_data.delete('_next_plugin_msg')
            gui.ok(plugin_msg)

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