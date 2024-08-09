import sys
from six.moves.urllib_parse import parse_qsl, urlparse, urlencode

from slyguy import signals, _
from slyguy.constants import *
from slyguy.log import log
from slyguy.exceptions import RouterError, Exit


_routes = {}

# @router.add('_settings', settings)
def add(url, f):
    if url == None:
        url = f.__name__
    _routes[url.rstrip('/')] = f

# @router.route('_settings')
def route(url):
    def decorator(f):
        add(url, f)
        return f
    return decorator

def add_url_args(url, **kwargs):
    parsed = urlparse(url)
    if parsed.scheme.lower() != 'plugin':
        return url

    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update(**kwargs)
    path = parsed.path.rstrip('/') or params.pop(ROUTE_TAG, '')

    return build_url(path, _addon_id=parsed.netloc, **params)

# @router.parse_url('?_=_settings')
def parse_url(url):
    if url.startswith('?'):
        url = 'plugin://{}/{}'.format(ADDON_ID, url)

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    path = parsed.path.rstrip('/') or params.pop(ROUTE_TAG, '')

    params[ROUTE_URL_TAG] = url
    if len(sys.argv) > 3 and sys.argv[3].lower() == 'resume:true':
        params[ROUTE_RESUME_TAG] = True

    if params.pop(ROUTE_LIVE_TAG, None) != None or params.pop(ROUTE_LIVE_TAG_LEGACY, None) != None:
        params[ROUTE_LIVE_TAG] = True

    function = _routes.get(path)
    if not function:
        raise RouterError(_(_.ROUTER_NO_FUNCTION, raw_url=url, parsed_url=path))

    log('Router Parsed: \'{0}\' => {1} {2}'.format(url, function.__name__, params))

    return function, params

def url_for_func(func, **kwargs):
    for _url in _routes:
        if _routes[_url].__name__ == func.__name__:
            return build_url(_url, **kwargs)

    raise RouterError(_(_.ROUTER_NO_URL, function_name=func.__name__))

def url_for(func_or_url, **kwargs):
    if callable(func_or_url):
        return url_for_func(func_or_url, **kwargs)
    else:
        return build_url(func_or_url, **kwargs)

def build_url(_url, _addon_id=ADDON_ID, **kwargs):
    if not _url.startswith('/'):
        path = ''
        kwargs[ROUTE_TAG] = _url or None
    else:
        path = _url.rstrip('/')

    is_live = kwargs.pop(ROUTE_LIVE_TAG, False)
    no_resume = kwargs.pop(NO_RESUME_TAG, False)

    params = []
    for k in sorted(kwargs):
        if kwargs[k] == None:
            continue

        try: params.append((k, unicode(kwargs[k]).encode('utf-8')))
        except: params.append((k, kwargs[k]))

    if is_live:
        params.append((ROUTE_LIVE_TAG, '1'))

    if is_live or no_resume:
        params.append((NO_RESUME_TAG, NO_RESUME_SUFFIX))

    return 'plugin://{}{}/?{}'.format(_addon_id, path, urlencode(params))

def redirect(url):
    log.debug('Redirect -> {}'.format(url))
    function, params = parse_url(url)
    function(**params)
    raise Exit()


# router.dispatch('?_=_settings')
def dispatch(url=None):
    if url is None:
        if hasattr(sys, 'listitem'):
            url = ROUTE_CONTEXT
            try:
                #Kodi 19+ only
                url += '?' + sys.argv[1]
            except IndexError:
                pass
            sys.argv = [sys.argv[0], -1, '']
        elif sys.argv[0].lower().endswith('.py'):
            url = ROUTE_SCRIPT
            try:
                #Kodi 19+ only
                url += '?' + sys.argv[1]
            except IndexError:
                pass
            sys.argv = [sys.argv[0], -1, '']
        else:
            url = sys.argv[0] + sys.argv[2]

    with signals.throwable():
        signals.emit(signals.BEFORE_DISPATCH)
        function, params = parse_url(url)

        if hasattr(sys, 'listitem'):
            params['listitem'] = sys.listitem

        try:
            function(**params)
        except TypeError as e:
            try: error = str(e)
            except: error = ''

            if error.startswith(function.__name__):
                raise RouterError(_.ROUTER_NO_FUNCTION)
            else:
                raise

    signals.emit(signals.AFTER_DISPATCH)


signals.emit(signals.ON_ENTRY)
if KODI_VERSION >= 19:
    import atexit
    atexit.register(lambda: signals.emit(signals.ON_EXIT))
