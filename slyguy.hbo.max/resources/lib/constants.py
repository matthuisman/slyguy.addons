DEVICE_MODEL = 'androidtv'

VERSION = '100.35.0.280'

HEADERS = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 8.1.0; SHIELD Android TV Build/LMY47D)',
    'X-Hbo-Device-Name': DEVICE_MODEL,
    'X-Hbo-Client-Version': 'Hadron/{0} android/{0} (SHIELD/8.1.0)'.format(VERSION),
    'X-Hbo-Device-Os-Version': '8.1.0',
    'Accept': 'application/vnd.hbo.v9.full+json',
    'Accept-Language': 'en-us',
}

UUID_NAMESPACE = '124f1611-0232-4336-be43-e054c8ecd0d5'
CLIENT_ID = 'c8d75990-06e5-445c-90e6-d556d7790998' #androidtv

CONFIG_URL = 'https://sessions.api.hbo.com/sessions/v1/clientConfig'
GUEST_AUTH = 'https://oauth.api.hbo.com/auth/tokens'
UPLOAD_AVATAR = '/accounts/user-images/profile/{image_id}?format=png&size=320x320&authorization=Bearer {token}'
CHARACTER_AVATAR = '/images/{image_id}/avatar?size=320x320'
DEVICE_CODE_URL = 'https://hbomax.com/tvsignin'
