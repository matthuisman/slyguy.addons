import logging

from ._helper import (
    InstanceStoreMixin,
    add_accept_encoding_header,
)
from .common import (
    Features,
    RequestHandler,
    Response,
    register_preference,
    register_rh,
)
from .exceptions import (
    CertificateVerifyError,
    HTTPError,
    ProxyError,
    RequestError,
    SSLError,
    TransportError,
)

SUPPORTED_ENCODINGS = [
    'gzip', 'deflate',
]


import requests
import urllib3.connection
import urllib3.exceptions


from slyguy.session import Session


class RequestsResponseAdapter(Response):
    def __init__(self, res):
        super().__init__(
            fp=res.raw, headers=res.headers, url=res.url,
            status=res.status_code, reason=res.reason)

        self._requests_response = res

    def read(self, amt = None):
        try:
            # Interact with urllib3 response directly.
            return self.fp.read(amt, decode_content=True)

        # See urllib3.response.HTTPResponse.read() for exceptions raised on read
        except urllib3.exceptions.SSLError as e:
            raise SSLError(cause=e) from e

        except urllib3.exceptions.ProtocolError as e:
            raise TransportError(cause=e) from e

        except urllib3.exceptions.HTTPError as e:
            # catch-all for any other urllib3 response exceptions
            raise TransportError(cause=e) from e

class Urllib3LoggingFilter(logging.Filter):

    def filter(self, record):
        # Ignore HTTP request messages since HTTPConnection prints those
        return record.msg != '%s://%s:%s "%s %s %s" %s %s'


class Urllib3LoggingHandler(logging.Handler):
    """Redirect urllib3 logs to our logger"""

    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self._logger.error(msg)
            else:
                self._logger.stdout(msg)

        except Exception:
            self.handleError(record)


@register_rh
class RequestsRH(RequestHandler, InstanceStoreMixin):
    _SUPPORTED_URL_SCHEMES = ('http', 'https')
    _SUPPORTED_ENCODINGS = tuple(SUPPORTED_ENCODINGS)
    _SUPPORTED_PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    RH_NAME = 'slyguy'

    def close(self):
        self._clear_instances()

    def _check_extensions(self, extensions):
        super()._check_extensions(extensions)
        extensions.pop('cookiejar', None)
        extensions.pop('timeout', None)
        extensions.pop('legacy_ssl', None)

    def _create_instance(self, cookiejar, legacy_ssl_support=None):
        session = Session()
        session.cookies = cookiejar
        return session

    def _send(self, request):
        headers = self._merge_headers(request.headers)
        add_accept_encoding_header(headers, SUPPORTED_ENCODINGS)

        max_redirects_exceeded = False

        session = self._get_instance(
            cookiejar=self._get_cookiejar(request),
            legacy_ssl_support=request.extensions.get('legacy_ssl'),
        )

        try:
            requests_res = session.request(
                method=request.method,
                url=request.url,
                data=request.data,
                headers=headers,
                timeout=self._calculate_timeout(request),
                allow_redirects=True,
                stream=True,
            )

        except requests.exceptions.TooManyRedirects as e:
            max_redirects_exceeded = True
            requests_res = e.response

        except requests.exceptions.SSLError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                raise CertificateVerifyError(cause=e) from e
            raise SSLError(cause=e) from e

        except requests.exceptions.ProxyError as e:
            raise ProxyError(cause=e) from e

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            raise TransportError(cause=e) from e

        except urllib3.exceptions.HTTPError as e:
            # Catch any urllib3 exceptions that may leak through
            raise TransportError(cause=e) from e

        except requests.exceptions.RequestException as e:
            # Miscellaneous Requests exceptions. May not necessary be network related e.g. InvalidURL
            raise RequestError(cause=e) from e

        res = RequestsResponseAdapter(requests_res)

        if not 200 <= res.status < 300:
            raise HTTPError(res, redirect_loop=max_redirects_exceeded)

        return res


@register_preference(RequestsRH)
def requests_preference(rh, request):
    return 2000
