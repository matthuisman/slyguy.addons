import json
import socket
import shutil
import re
from gzip import GzipFile

import requests
import urllib3
from six import BytesIO
from six.moves.urllib_parse import urlparse
from kodi_six import xbmc
import dns.resolver

from . import userdata, settings, signals
from .util import get_kodi_proxy
from .smart_urls import get_dns_rewrites
from .log import log
from .language import _
from .exceptions import SessionError, Error
from .constants import DEFAULT_USERAGENT, CHUNK_SIZE, KODI_VERSION

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_HEADERS = {
    'User-Agent': DEFAULT_USERAGENT,
}

def json_override(func, error_msg):
    try:
        return func()
    except Exception as e:
        raise SessionError(error_msg or _.JSON_ERROR)

orig_getaddrinfo = socket.getaddrinfo

CIPHERS_STRING = '@SECLEVEL=1:'+requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS
class SSLAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = requests.packages.urllib3.util.ssl_.create_urllib3_context(ciphers=CIPHERS_STRING)
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = requests.packages.urllib3.util.ssl_.create_urllib3_context(ciphers=CIPHERS_STRING)
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).proxy_manager_for(*args, **kwargs)


SESSIONS = []
@signals.on(signals.AFTER_DISPATCH)
def close_sessions():
    for session in SESSIONS:
        session.close()

class RawSession(requests.Session):
    def __init__(self, verify=None, timeout=None, auto_close=True):
        super(RawSession, self).__init__()
        self._verify = verify
        self._timeout = timeout
        self._session_cache = {}
        self._rewrites = []
        self._proxy = None
        self._cert = None
        if auto_close:
            SESSIONS.append(self)

        # Py3 only. Py2 works without and this breaks it
        if KODI_VERSION > 18:
            self.mount('https://', SSLAdapter())

    def set_dns_rewrites(self, rewrites):
        for entries in rewrites:
            pattern = entries.pop()
            pattern = re.escape(pattern).replace('\*', '.*')
            pattern = re.compile(pattern, flags=re.IGNORECASE)

            new_entries = []
            for entry in entries:
                _type = 'skip'
                if entry.startswith('>'):
                    _type = 'proxy'
                    entry = entry[1:]
                elif entry.startswith('r:'):
                    _type = 'resolver'
                    entry = entry[2:]
                elif entry[0].isdigit():
                    _type = 'dns'
                else:
                    _type = 'url_sub'
                new_entries.append([_type, entry])

            # Make sure dns is done last
            self._rewrites.append([pattern, sorted(new_entries, key=lambda x: x[0] == 'dns')])

    def set_cert(self, cert):
        self._cert = cert
        log.debug('Cert set to: {}'.format(cert))

    def _get_cert(self):
        if not self._cert:
            return None

        if self._cert.lower().startswith('http'):
            url = self._cert
            self._cert = None

            log.debug('Downloading cert: {}'.format(url))
            resp = self.request('get', url, stream=True)

            self._cert = xbmc.translatePath('special://temp/temp.pem')
            with open(self._cert, 'wb') as f:
                shutil.copyfileobj(resp.raw, f)

        return xbmc.translatePath(self._cert)

    def set_proxy(self, proxy):
        self._proxy = proxy

    def _get_proxy(self):
        if self._proxy and self._proxy.lower().strip() == 'kodi':
            self._proxy = get_kodi_proxy()
        return self._proxy

    def __del__(self):
        self.close()

    def request(self, method, url, **kwargs):
        req = requests.Request(method, url, params=kwargs.pop('params', None))
        url = req.prepare().url

        session_data = {
            'proxy': None,
            'rewrite': None,
            'resolver': None,
            'url': url,
        }

        if url in self._session_cache:
            session_data = self._session_cache[url]
        elif self._rewrites:
            for row in self._rewrites:
                if not row[0].search(url):
                    continue

                for entry in row[1]:
                    if entry[0] == 'skip':
                        continue
                    if entry[0] == 'url_sub':
                        session_data['url'] = re.sub(row[0], entry[1], url, count=1)
                    elif entry[0] == 'proxy':
                        session_data['proxy'] = entry[1]
                    elif entry[0] == 'dns':
                        session_data['rewrite'] = [urlparse(session_data['url']).netloc.lower(), entry[1]]
                    elif entry[0] == 'resolver' and entry[1]:
                        resolver = dns.resolver.Resolver(configure=False)
                        resolver.cache = dns.resolver.Cache()
                        resolver.nameservers = [entry[1],]
                        session_data['resolver'] = [urlparse(session_data['url']).netloc.lower(), resolver]
                break

            self._session_cache[url] = session_data

        def connection_from_pool_key(self, pool_key, request_context=None):
            # ensure we get a unique pool (socket) for same domain on different rewrite ips
            if session_data['rewrite'] and session_data['rewrite'][0] == request_context['host']:
                pool_key = pool_key._replace(key_server_hostname=session_data['rewrite'][1])
            # ensure we get a unique pool (socket) for same domain on different resolvers
            elif session_data['resolver'] and session_data['resolver'][0] == request_context['host']:
                pool_key = pool_key._replace(key_server_hostname=session_data['resolver'][1].nameservers[0])
            return orig_connection_from_pool_key(self, pool_key, request_context)

        def getaddrinfo(host, port, family=0, _type=0, proto=0, flags=0):
            orig_host = host

            if session_data['rewrite'] and session_data['rewrite'][0] == host:
                host = session_data['rewrite'][1]
                log.debug("DNS Rewrite: {} -> {}".format(orig_host, host))

            elif session_data['resolver'] and session_data['resolver'][0] == host:
                host = session_data['resolver'][1].query(host)[0].to_text()
                log.debug('DNS Resolver: {} -> {} -> {}'.format(orig_host, session_data['resolver'][1].nameservers[0], host))

            try:
                addresses = orig_getaddrinfo(host, port, socket.AF_INET, _type, proto, flags)
            except socket.gaierror:
                addresses = orig_getaddrinfo(host, port, socket.AF_INET6, _type, proto, flags)

            return addresses

        if session_data['url'] != url:
            log.debug("URL Changed: {}".format(session_data['url']))

        if session_data['proxy'] is None:
            session_data['proxy'] = self._get_proxy()

        if session_data['proxy']:
            # remove username, password from proxy for logging
            parsed = urlparse(session_data['proxy'])
            replaced = parsed._replace(netloc="{}:{}@{}".format('username', 'password', parsed.hostname) if parsed.username else parsed.hostname)
            log.debug("Proxy: {}".format(replaced.geturl()))

            kwargs['proxies'] = {
                'http': session_data['proxy'],
                'https': session_data['proxy'],
            }

        if self._cert:
            kwargs['verify'] = False
            kwargs['cert'] = self._get_cert()

        if 'verify' not in kwargs:
            kwargs['verify'] = self._verify

        if 'timeout' not in kwargs:
            kwargs['timeout'] = self._timeout

        # Save pointers to original functions
        orig_getaddrinfo = socket.getaddrinfo
        orig_connection_from_pool_key = urllib3.PoolManager.connection_from_pool_key

        try:
            if session_data['rewrite'] or session_data['resolver']:
                # Override functions
                socket.getaddrinfo = getaddrinfo
                urllib3.PoolManager.connection_from_pool_key = connection_from_pool_key

            # Do request
            result = super(RawSession, self).request(method, session_data['url'], **kwargs)
        finally:
            # Revert functions to original
            socket.getaddrinfo = orig_getaddrinfo
            urllib3.PoolManager.connection_from_pool_key = orig_connection_from_pool_key

        return result

class Session(RawSession):
    def __init__(self, headers=None, cookies_key=None, base_url='{}', timeout=None, attempts=None, verify=None, dns_rewrites=None, auto_close=True):
        super(Session, self).__init__(verify=settings.common_settings.getBool('verify_ssl', True) if verify is None else verify,
            timeout=settings.common_settings.getInt('http_timeout', 30) if timeout is None else timeout, auto_close=auto_close)

        self._headers = headers or {}
        self._cookies_key = cookies_key
        self._base_url = base_url
        self._attempts = settings.common_settings.getInt('http_retries', 2) if attempts is None else attempts
        self.before_request = None
        self.after_request = None

        self.set_dns_rewrites(get_dns_rewrites() if dns_rewrites is None else dns_rewrites)
        self.set_proxy(settings.get('proxy_server') or settings.common_settings.get('proxy_server'))

        self.headers.update(DEFAULT_HEADERS)
        self.headers.update(self._headers)

        if self._cookies_key:
            self.cookies.update(userdata.get(self._cookies_key, {}))

    def gz_json(self, *args, **kwargs):
        resp = self.get(*args, **kwargs)
        json_text = GzipFile(fileobj=BytesIO(resp.content)).read()
        return json.loads(json_text)

    def request(self, method, url, timeout=None, attempts=None, verify=None, error_msg=None, retry_not_ok=False, retry_delay=1000, log_url=None, **kwargs):
        method = method.upper()

        if not url.startswith('http'):
            url = self._base_url.format(url)

        attempts = self._attempts if attempts is None else attempts

        if timeout is not None:
            kwargs['timeout'] = timeout

        if verify is not None:
            kwargs['verify'] = verify

        for i in range(1, attempts+1):
            attempt = 'Attempt {}/{}: '.format(i, attempts)
            if i > 1 and retry_delay:
                xbmc.sleep(retry_delay)

            if self.before_request:
                self.before_request()

            log('{}{} {}'.format(attempt, method, log_url or url))

            try:
                resp = super(Session, self).request(method, url, **kwargs)
            except:
                resp = None
                if i == attempts:
                    raise
                else:
                    continue

            if resp is None:
                raise SessionError(error_msg or _.NO_RESPONSE_ERROR)

            if retry_not_ok and not resp.ok:
                continue
            else:
                break

        resp.json = lambda func=resp.json, error_msg=error_msg: json_override(func, error_msg)

        if self.after_request:
            self.after_request(resp)

        return resp

    def save_cookies(self):
        if not self._cookies_key:
            raise Exception('A cookies key needs to be set to save cookies')

        userdata.set(self._cookies_key, self.cookies.get_dict())

    def clear_cookies(self):
        if self._cookies_key:
            userdata.delete(self._cookies_key)
        self.cookies.clear()

    def chunked_dl(self, url, dst_path, method='GET', **kwargs):
        kwargs['stream'] = True
        resp = self.request(method, url, **kwargs)
        resp.raise_for_status()

        with open(dst_path, 'wb') as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                f.write(chunk)

        return resp

def gdrivedl(url, dst_path):
    if 'drive.google.com' not in url.lower():
        raise Error('Not a gdrive url')

    ID_PATTERNS = [
        re.compile('/file/d/([0-9A-Za-z_-]{10,})(?:/|$)', re.IGNORECASE),
        re.compile('id=([0-9A-Za-z_-]{10,})(?:&|$)', re.IGNORECASE),
        re.compile('([0-9A-Za-z_-]{10,})', re.IGNORECASE)
    ]
    FILE_URL = 'https://docs.google.com/uc?export=download&id={id}&confirm={confirm}'
    CONFIRM_PATTERN = re.compile("download_warning[0-9A-Za-z_-]+=([0-9A-Za-z_-]+);", re.IGNORECASE)
    FILENAME_PATTERN = re.compile('attachment;filename="(.*?)"', re.IGNORECASE)

    id = None
    for pattern in ID_PATTERNS:
        match = pattern.search(url)
        if match:
            id = match.group(1)
            break

    if not id:
        raise Error('No file ID find in gdrive url')

    with Session() as session:
        resp = session.get(FILE_URL.format(id=id, confirm=''), stream=True)
        if not resp.ok:
            raise Error('Gdrive url no longer exists')

        if 'ServiceLogin' in resp.url:
            raise Error('Gdrive url does not have link sharing enabled')

        cookies = resp.headers.get('Set-Cookie') or ''
        if 'download_warning' in cookies:
            confirm = CONFIRM_PATTERN.search(cookies)
            resp = session.get(FILE_URL.format(id=id, confirm=confirm.group(1)), stream=True)

        filename = FILENAME_PATTERN.search(resp.headers.get('content-disposition')).group(1)
        dst_path = dst_path if os.path.isabs(dst_path) else os.path.join(dst_path, filename)

        resp.raise_for_status()
        with open(dst_path, 'wb') as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                f.write(chunk)

    return filename
