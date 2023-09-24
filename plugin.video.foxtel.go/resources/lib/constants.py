HEADERS = {
    'user-agent': 'GO2/6.0.0.J/Phone/ANDROID/8.1.0/S22',
    'Accept': '',
    'Accept-Encoding': 'gzip',
    'Cache-Control': 'no-cache',
    'Pragma': 'gzip',
}

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
