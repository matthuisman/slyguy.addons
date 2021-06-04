HEADERS = {
    'User-Agent': 'okhttp/2.7.5',
}

LIVE_SITEID = '206'
VOD_SITEID  = '296'

BASE_URL = 'https://foxtel-go-sw.foxtelplayer.foxtel.com.au/now-atv-150'
API_URL = BASE_URL + '/api{}'
BUNDLE_URL = BASE_URL + '/bundleAPI/getHomeBundle.php'
IMG_URL = BASE_URL + '/imageHelper.php?id={id}:png&w={width}{fragment}'
SEARCH_URL = 'https://foxtel-prod-elb.digitalsmiths.net/sd/foxtel/taps/assets/search/prefix'
EPG_URL = 'https://foxtel-go-sw.foxtelplayer.foxtel.com.au/go-mobile-440/api/epg.class.api.php/getChannelListings/' + LIVE_SITEID

AES_IV = 'b2d40461b54d81c8c6df546051370328'
PLT_DEVICE = 'andr_screen'
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
