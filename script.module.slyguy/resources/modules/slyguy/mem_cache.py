from time import time
from functools import wraps
from copy import deepcopy

from six.moves import cPickle

from slyguy import signals, router
from slyguy.log import log
from slyguy.util import hash_6, set_kodi_string, get_kodi_string
from slyguy.constants import ADDON_ID, CACHE_EXPIRY, ROUTE_CLEAR_CACHE, ADDON_VERSION, KODI_VERSION


cache_key = 'cache.'+ADDON_ID+ADDON_VERSION
class Cache(object):
    data = None
cache = Cache()


def _get_cache():
    if cache.data is None:
        cache.data = {}

        if KODI_VERSION < 18:
            data = get_kodi_string(cache_key)
            if data:
                set_kodi_string(cache_key, "")
                try:
                    cache.data = cPickle.loads(data.encode('latin1')) or {}
                except Exception as e:
                    log.debug('Memcache: load failed: {}'.format(e))
                else:
                    log.debug("Memcache: loaded from kodi string")

    return cache.data


def set(key, value, expires=CACHE_EXPIRY):
    if expires == 0:
        return

    elif expires != None:
        expires = int(time() + expires)

    log('Cache Set: {}'.format(key))
    _get_cache()[key] = [deepcopy(value), expires]


def get(key, default=None):
    cache = _get_cache()
    try:
        row = cache[key]
    except KeyError:
        return default

    if row[1] != None and row[1] < time():
        cache.pop(key, None)
        return default
    else:
        log('Cache Hit: {}'.format(key))
        return deepcopy(row[0])


def delete(key):
    if int(_get_cache().pop(key, None) != None):
        log('Cache Delete: {}'.format(key))
        return True
    return False


def empty():
    cache = _get_cache()
    deleted = len(cache)
    cache.clear()
    log('Memcache: Deleted {} Rows'.format(deleted))


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


@signals.on(signals.ON_EXIT)
def remove_expired():
    if KODI_VERSION < 18:
        log('Memcache: persisting via kodi string')
        set_kodi_string(cache_key, cPickle.dumps(cache.data or {}, protocol=0).decode('latin1'))


@router.route(ROUTE_CLEAR_CACHE)
def clear_cache(key, **kwargs):
    delete(key)
