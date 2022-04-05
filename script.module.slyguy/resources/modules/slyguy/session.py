import json
import socket
import re
from gzip import GzipFile

import requests
from six import BytesIO
from kodi_six import xbmc

from . import userdata, settings
from .dns import get_dns_rewrites
from .log import log
from .language import _
from .exceptions import SessionError
from .constants import DEFAULT_USERAGENT, CHUNK_SIZE

DEFAULT_HEADERS = {
    'User-Agent': DEFAULT_USERAGENT,
}

def json_override(func, error_msg):
    try:
        return func()
    except Exception as e:
        raise SessionError(error_msg or _.JSON_ERROR)

orig_getaddrinfo = socket.getaddrinfo

class RawSession(requests.Session):
    def __init__(self, verify=None, timeout=None):
        super(RawSession, self).__init__()
        self._timeout = settings.common_settings.getInt('http_timeout', 30) if timeout is None else timeout
        self._verify = settings.common_settings.getBool('verify_ssl', True) if verify is None else verify
        self._dns_rewrites = []
        self._rewrite_cache = {}
        socket.getaddrinfo = lambda *args, **kwargs: self._getaddrinfoPreferIPv4(*args, **kwargs)

    def set_dns_rewrites(self, rewrites):
        self._dns_rewrites = rewrites
        self._rewrite_cache = {}

    def _getaddrinfoPreferIPv4(self, host, port, family=0, _type=0, proto=0, flags=0):
        if host in self._rewrite_cache:
            host = self._rewrite_cache[host]
        elif self._dns_rewrites:
            for ip in self._dns_rewrites:
                pattern = ip[0].replace('.', '\.').replace('*', '.*')
                if re.match(pattern, host, flags=re.IGNORECASE):
                    log.debug("DNS Rewrite: {}: {} -> {}".format(ip[0], host, ip[1]))
                    self._rewrite_cache[host] = ip[1]
                    host = ip[1]
                    break

        try:
            return orig_getaddrinfo(host, port, socket.AF_INET, _type, proto, flags)
        except socket.gaierror:
            log.debug('Fallback to ipv6 addrinfo')
            return orig_getaddrinfo(host, port, socket.AF_INET6, _type, proto, flags)

    def request(self, method, url, **kwargs):
        if 'verify' not in kwargs:
            kwargs['verify'] = self._verify
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self._timeout
        return super(RawSession, self).request(method, url, **kwargs)


def _remove_proxy_authorization(proxy):
    return re.sub(r"^(?P<protocol>[a-zA-Z]+):\/\/((?P<userinfo>.*)@)?(?P<host>[^:]+)(:(?P<port>[0-9]+))?$",
                  "\\g<protocol>://\\g<host>\\5", proxy, 1)


class Session(RawSession):
    def __init__(self, headers=None, cookies_key=None, base_url='{}', timeout=None, attempts=None, verify=None, dns_rewrites=None):
        super(Session, self).__init__(verify, timeout)

        self._headers = headers or {}
        self._cookies_key = cookies_key
        self._base_url = base_url
        self._attempts = settings.common_settings.getInt('http_retries', 2) if attempts is None else attempts
        self.before_request = None
        self.after_request = None

        self.set_dns_rewrites(get_dns_rewrites() if dns_rewrites is None else dns_rewrites)

        self.headers.update(DEFAULT_HEADERS)
        self.headers.update(self._headers)

        if self._cookies_key:
            self.cookies.update(userdata.get(self._cookies_key, {}))

        self._set_proxies(settings.get('proxy'))

    def _set_proxies(self, proxy):
        if not proxy:
            log.debug('NO PROXY')
            return

        log.debug('PROXY: {}'.format(_remove_proxy_authorization(proxy)))
        proxies = {
            "http": proxy,
            "https": proxy
        }
        self.proxies.update(proxies)
        try:
            country_code = self.get(url='https://ifconfig.io/country_code').text
        except BaseException as ex:
            log.error('PROXY TEST FAILED: {}'.format(ex))
            country_code = 'FAIL'
        log.debug('COUNTRY CODE: {}'.format(country_code))

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

        #url = PROXY_PATH + url

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
