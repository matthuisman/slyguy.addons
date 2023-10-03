import random
from hashlib import md5
from collections import OrderedDict

SSL_CIPHERS = 'AES128-GCM-SHA256:AES256-GCM-SHA384:CHACHA20-POLY1305-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA:AES256-SHA'
SSL_CIPHERS = SSL_CIPHERS.split(':')
random.shuffle(SSL_CIPHERS)
SSL_CIPHERS = ':'.join(SSL_CIPHERS)
SSL_OPTIONS = 0
APP_VERSION = '2.1.2'
USER_AGENT = 'platform/{}/{}'.format(APP_VERSION, md5('agent/apps/android/kayo'.encode()).hexdigest())

HEADERS = OrderedDict([
    ('accept-language', 'en_US'),
    ('auth0-client', 'eyJuYW1lIjoiQXV0aDAuQW5kcm9pZCIsImVudiI6eyJhbmRyb2lkIjoiMzAifSwidmVyc2lvbiI6IjIuNy4wIn0='),
    ('user-agent', USER_AGENT),
    # ('traceparent', '......'),
    # ('newrelic', '....'),
    # ('tracestate', '....'),
    # ('content-type', 'application/json; charset=utf-8'),
    # ('content-length', ''),
    # ('accept-encoding', 'gzip'),
    # ('x-newrelic-id', '.....'),
])

PLAY_HEADERS = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; SHIELD Android TV Build/PPR1.180610.011)',
}

AUTH_URL = 'https://auth.streamotion.com.au/oauth'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
