from slyguy.constants import ADDON_ID

if ADDON_ID == 'plugin.video.foxtel.now':
    APP_ID = 'PLAY2'
    URL    = 'now-mobile-140'
else:
    APP_ID = 'GO2'
    URL    = 'go-mobile-440'

HEADERS = {
    'User-Agent': 'okhttp/2.7.5',
}

BASE_URL     = 'https://foxtel-go-sw.foxtelplayer.foxtel.com.au/{}'.format(URL)
API_URL      = BASE_URL + '/api{}'
BUNDLE_URL   = BASE_URL + '/bundleAPI/getHomeBundle.php'
IMG_URL      = BASE_URL + '/imageHelper.php?id={id}:png&w={width}{fragment}'
SEARCH_URL   = 'https://foxtel-prod-elb.digitalsmiths.net/sd/foxtel/taps/assets/search/prefix'

AES_IV = 'b2d40461b54d81c8c6df546051370328'
PLT_DEVICE = 'andr_phone'
EPG_EVENTS_COUNT = 6

TYPE_LIVE  = '1'
TYPE_VOD   = '2'

LIVE_SITEID = '206'
VOD_SITEID  = '296'

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