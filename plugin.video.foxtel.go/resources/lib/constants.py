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
  #  ('auth0-client', 'eyJuYW1lIjoiQXV0aDAuQW5kcm9pZCIsImVudiI6eyJhbmRyb2lkIjoiMzAifSwidmVyc2lvbiI6IjIuNy4wIn0='),
    ('user-agent', USER_AGENT),
    # ('traceparent', '......'),
    # ('newrelic', '....'),
    # ('tracestate', '....'),
    # ('content-type', 'application/json; charset=utf-8'),
    # ('content-length', ''),
    # ('accept-encoding', 'gzip'),
    # ('x-newrelic-id', '.....'),
])

LIVE_SITEID = '206'
VOD_SITEID  = '296'

DEFAULT_NICKNAME = 'Kodi-{mac_address} on {system}'
DEFAULT_DEVICEID = '{username}{mac_address}'

BASE_URL = 'https://foxtel-go-sw.foxtelplayer.foxtel.com.au/go-mobile-570'
API_URL = BASE_URL + '/api{}'
BUNDLE_URL = BASE_URL + '/bundleAPI/getHomeBundle.php'
IMG_URL = BASE_URL + '/imageHelper.php?id={id}:png&w={width}{fragment}'

SEARCH_URL = 'https://foxtel-prod-elb.digitalsmiths.net/sd/foxtel/taps/assets/search/prefix'
PLAY_URL = 'https://foxtel-go-sw.foxtelplayer.foxtel.com.au/now-box-140/api/playback.class.api.php/{endpoint}/{site_id}/1/{id}'
LIVE_DATA_URL = 'https://i.mjh.nz/Foxtel/app.json'
EPG_URL = 'https://i.mjh.nz/Foxtel/epg.xml.gz'

AES_IV = 'b2d40461b54d81c8c6df546051370328'
PLT_DEVICE = 'andr_phone'
EPG_EVENTS_COUNT = 6

TYPE_LIVE  = '1'
TYPE_VOD   = '2'

ASSET_MOVIE  = '1'
ASSET_TVSHOW = '4'
ASSET_BOTH   = ''

STREAM_PRIORITY = {
    'WIREDHD'  : 16,
    'WIREDHIGH': 15,
    'WIFIHD'   : 14,
    'WIFIHIGH' : 13,
    'FULL'     : 12,
    'WIFILOW'  : 11,
    '3GHIGH'   : 10,
    '3GLOW'    : 9,
    'DEFAULT'  : 0,
}
