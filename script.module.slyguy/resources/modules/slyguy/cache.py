from time import time
from functools import wraps

import peewee

from slyguy import database, settings, signals, gui, router, log, _
from slyguy.constants import CACHE_TABLENAME, CACHE_EXPIRY, CACHE_CHECKSUM, ROUTE_CLEAR_CACHE
from slyguy.util import hash_6

funcs = []

class Cache(database.Model):
    checksum = CACHE_CHECKSUM

    key     = database.HashField(unique=True)
    value   = database.PickleField()
    expires = peewee.IntegerField()

    class Meta:
        table_name = CACHE_TABLENAME

def enabled():
    return settings.getBool('use_cache', True)

def key_for(f, *args, **kwargs):
    func_name = f.__name__ if callable(f) else f
    if not enabled() or func_name not in funcs:
        return None

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
            _key = key or _build_key(f.__name__, *args, **kwargs)
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

        funcs.append(f.__name__)
        return decorated_function

    return lambda f: decorator(f, *args, **kwargs)

def get(key, default=None):
    if not enabled():
        return default

    try:
        return Cache.get(Cache.key == key, Cache.expires > time()).value
    except Cache.DoesNotExist:
        return default

def set(key, value, expires=CACHE_EXPIRY):
    expires = int(time() + expires)
    Cache.set(key=key, value=value, expires=expires)

def delete(key):
    return Cache.delete_where(Cache.key == key)

def empty():
    deleted = Cache.truncate()
    log('Cache: Deleted {} Rows'.format(deleted))

@signals.on(signals.BEFORE_DISPATCH)
def remove_expired():
    deleted = Cache.delete_where(Cache.expires < int(time()))
    log('Cache: Deleted {} Expired Rows'.format(deleted))

@router.route(ROUTE_CLEAR_CACHE)
def clear_cache(key, **kwargs):
    delete_count = delete(key)
    msg = _(_.PLUGIN_CACHE_REMOVED, delete_count=delete_count)
    gui.notification(msg)


database.init([Cache])
