from slyguy import settings

HEADERS = {
    'user-agent': 'okhttp/3.14.2',
}

IMG_URL = 'https://wwwimage-us.pplusstatic.com/thumbnails/photos/{dimensions}/{file}'
LINK_PLATFORM_URL = 'https://link.theplatform.com/s/{account}/{pid}'

AES_KEY = '302a6a0d70a7e9b967f91d39fef3e387816e3095925ae4537bce96063311f9c5'
TV_SECRET = '415f7ae1f42f5cec'
PHONE_SECRET = '003ff1f049feb54a'

REGION_US = {
    'country_code': 'US',
    'base_url': 'https://www.paramountplus.com',
}

REGION_CA = {
    'country_code': 'CA',
    'base_url': 'https://tv.cbs.com',
}

REGION_AU = {
    'country_code': 'AU',
    'base_url': 'https://www.tenallaccess.com.au',
}

REGIONS  = [REGION_US, REGION_CA, REGION_AU]

REGION = settings.getEnum('region_index', REGIONS, default=REGION_US)

API_URL = REGION['base_url'] + '/apps-api{}'
DEVICE_LINK_URL = REGION['base_url'] + '/androidtv'
IP_URL = REGION['base_url'] + '/apps/user/ip.json'
COUNTRY_CODE = REGION['country_code']
