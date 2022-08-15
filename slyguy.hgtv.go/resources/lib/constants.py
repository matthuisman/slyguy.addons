BOOTSTRAP_URL = 'https://global-prod.disco-api.com/bootstrapInfo'
CLIENT_ID = 'd6566ea096b61ebb7a85'
SITE_ID = 'hgtv'
BID = 'hgtv'
APP_VERSION = '3.0.25'

HEADERS = {
    'x-disco-client': 'ANDROIDTV:27:{}:{}'.format(SITE_ID, APP_VERSION),
    'x-disco-params': 'bid={}'.format(BID),
    'user-agent': 'Mozilla/5.0 (Linux; Android 8.1.0; sdk_google_atv_x86 Build/OSM1.180201.036; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.98 Mobile Safari/537.36',
}
