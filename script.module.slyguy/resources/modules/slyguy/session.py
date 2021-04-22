import json
import socket
from gzip import GzipFile

import requests
from six import BytesIO

from . import userdata, settings
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

def getaddrinfoPreferIPv4(host, port, family=0, _type=0, proto=0, flags=0):
    try:
        return orig_getaddrinfo(host, port, socket.AF_INET, _type, proto, flags)
    except socket.gaierror:
        log.debug('Fallback to ipv6 addrinfo')
        return orig_getaddrinfo(host, port, socket.AF_INET6, _type, proto, flags)

socket.getaddrinfo = getaddrinfoPreferIPv4

class RawSession(requests.Session):
    pass

class Session(RawSession):
    def __init__(self, headers=None, cookies_key=None, base_url='{}', timeout=None, attempts=None, verify=None):
        super(Session, self).__init__()

        self._headers     = headers or {}
        self._cookies_key = cookies_key
        self._base_url    = base_url
        self._timeout     = timeout or settings.getInt('http_timeout', 30)
        self._attempts    = attempts or settings.getInt('http_retries', 2)
        self._verify      = verify if verify is not None else settings.getBool('verify_ssl', True)
        self.after_request = None

        self.headers.update(DEFAULT_HEADERS)
        self.headers.update(self._headers)

        if self._cookies_key:
            self.cookies.update(userdata.get(self._cookies_key, {}))

    def gz_json(self, *args, **kwargs):
        resp = self.get(*args, **kwargs)
        json_text = GzipFile(fileobj=BytesIO(resp.content)).read()
        return json.loads(json_text)

    def request(self, method, url, timeout=None, attempts=None, verify=None, error_msg=None, **kwargs):
        method = method.upper()

        if not url.startswith('http'):
            url = self._base_url.format(url)

        timeout = timeout or self._timeout
        if timeout:
            kwargs['timeout'] = timeout

        kwargs['verify']  = verify or self._verify
        attempts          = attempts or self._attempts

        #url = PROXY_PATH + url

        for i in range(1, attempts+1):
            attempt = 'Attempt {}/{}: '.format(i, attempts) if i > 1 else ''

            try:
                log('{}{} {} {}'.format(attempt, method, url, kwargs if method != 'POST' else ""))
            except:
                log('{}{} {}'.format(attempt, method, url))

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