import sys
from time import time
from functools import wraps
from copy import deepcopy

from six.moves import cPickle

from . import signals, router
from .log import log
from .util import hash_6, set_kodi_string, get_kodi_string
from .constants import ADDON_ID, CACHE_EXPIRY, ROUTE_CLEAR_CACHE, ADDON_VERSION
from .settings import common_settings as settings

cache_key = 'cache.'+ADDON_ID+ADDON_VERSION

class Cache(object):
    data = {}

cache = Cache()

@signals.on(signals.BEFORE_DISPATCH)
def load():
    if not cache.data and settings.getBool('persist_cache', True):
        cache.data = {}

        try:
            data = get_kodi_string(cache_key)
            cache.data = cPickle.loads(data.encode('latin1'))
        except Exception as e:
            log.debug('load cache failed')
        else:
            log.debug('Cache data loaded')

        set_kodi_string(cache_key, "{}")

def set(key, value, expires=CACHE_EXPIRY):
    if expires == 0:
        return

    elif expires != None:
        expires = int(time() + expires)

    log('Cache Set: {}'.format(key))
    cache.data[key] = [deepcopy(value), expires]

def get(key, default=None):
    try:
        row = cache.data[key]
    except KeyError:
        return default

    if row[1] != None and row[1] < time():
        cache.data.pop(key, None)
        return default
    else:
        log('Cache Hit: {}'.format(key))
        return deepcopy(row[0])

def delete(key):
    if int(cache.data.pop(key, None) != None):
        log('Cache Delete: {}'.format(key))
        return True
    return False

def empty():
    deleted = len(cache.data)
    cache.data.clear()
    log('Mem Cache: Deleted {} Rows'.format(deleted))

def key_for(f, *args, **kwargs):
    func_name = f.__name__ if callable(f) else f
    return _build_key(func_name, *args, **kwargs)

def _build_key(func_name, *args, **kwargs):
    key = func_name.encode('utf8').decode('utf8')

    def to_str(item):
        try:
            return item.encode('utf8').decode('utf8')
        except:
            return str(item)

    def is_primitive(item):
        try:
            #python2
            return type(item) in (int, str, dict, list, bool, float, unicode)
        except:
            #python3
            return type(item) in (int, str, dict, list, bool, float)

    for k in args:
        if is_primitive(k):
            key += to_str(k)

    for k in sorted(kwargs):
        if is_primitive(kwargs[k]):
            key += to_str(k) + to_str(kwargs[k])

    return hash_6(key)

def cached(*args, **kwargs):
    def decorator(f, expires=CACHE_EXPIRY, key=None):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            _key = key or kwargs.pop('_cache_key', None) or _build_key(f.__name__, *args, **kwargs)
            if callable(_key):
                _key = _key(*args, **kwargs)

            if not kwargs.pop('_skip_cache', False):
                value = get(_key)
                if value != None:
                    log('Cache Hit: {}'.format(_key))
                    return value

            value = f(*args, **kwargs)
            if value != None:
                set(_key, value, expires)

            return value

        return decorated_function

    return lambda f: decorator(f, *args, **kwargs)

@signals.on(signals.AFTER_DISPATCH)
def remove_expired():
    _time = time()
    delete  = []

    for key in cache.data.keys():
        if cache.data[key][1] < _time:
            delete.append(key)

    for key in delete:
        cache.data.pop(key, None)

    if delete:
        log('Mem Cache: Deleted {} Expired Rows'.format(len(delete)))

    if settings.getBool('persist_cache', True):
        set_kodi_string(cache_key, cPickle.dumps(cache.data, protocol=0).decode('latin1'))
        cache.data.clear()

@router.route(ROUTE_CLEAR_CACHE)
def clear_cache(key, **kwargs):
    delete_count = delete(key)
