HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    # 'User-Agent': 'dstv-now-android-2.5.9',
    # 'api-consumer': 'DStvNowAndroid',
}

CLIENT_ID = 'dc09de02-de71-4181-9006-2754dc5d3ed3'
PRODUCT_ID = 'c53b19ce-62c0-441e-ad29-ecba2dcdb199'
PLATFORM_ID = '32faad53-5e7b-4cc0-9f33-000092e85950'
DEVICE_TYPE = 'Web'

DEFAULT_COUNTRY = 'ZA'
DEFAULT_PACKAGE = 'PREMIUM'
ZA_EPG_URL = 'https://i.mjh.nz/DStv/za.xml.gz'

UUID_NAMESPACE = '122e1611-0232-4336-bf43-e054c8ecd0d5'
WEBSOCKET_URL = 'wss://ws-eu.pusher.com/app/5b1cf858986ab7d6a9d7?client=java-client&protocol=5&version=2.0.1'
REFRESH_TOKEN_URL = 'https://ssl.dstv.com/connect/connect-authtoken/v2/accesstoken/refresh?build_nr=1.0.3'
API_URL = 'https://ssl.dstv.com/api{}'
LICENSE_URL = 'https://license.dstv.com/widevine/getLicense?CrmId=afl&AccountId=afl&ContentId={}&SessionId={}&Ticket={}'
TIMEOUT = (10, 20)

CONTENT_EXPIRY = (60*60*24) #24 hours
EPISODES_EXPIRY = (60*5) #5 Minutes
