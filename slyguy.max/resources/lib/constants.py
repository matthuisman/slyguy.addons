BASE_URL = 'https://default.any-any.prd.api.discomax.com'
CLIENT_ID = 'b6746ddc-7bc7-471f-a16c-f6aaf0c34d26'
SITE_ID = 'beam'
BRAND_ID = 'beam'
REALM = 'bolt'
APP_VERSION = '4.0.1'
PAGE_SIZE = 50
L3_MAX_HEIGHT = 580  #TODO: confirm actual limit for L3 or find better way (cenc data / lowest quality set?)

HEADERS = {
    'x-disco-client': 'ANDROIDTV:9:{}:{}'.format(SITE_ID, APP_VERSION),
    'x-disco-params': 'realm={},bid={},features=ar'.format(REALM, BRAND_ID),
    'user-agent': 'androidtv {}/{} (android/9; en-NZ; SHIELD Android TV-NVIDIA; Build/1)'.format(SITE_ID, APP_VERSION),
}
