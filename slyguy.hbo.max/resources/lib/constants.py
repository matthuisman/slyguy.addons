DEVICE_MODEL = 'androidtv'

HEADERS = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 8.1.0; SHIELD Android TV Build/LMY47D)',
    'X-Hbo-Client-Version': 'Hadron/50.35.0.280 android/50.35.0.280 (MI 5/8.1.0)',
    'X-Hbo-Device-Name': DEVICE_MODEL,
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

AGE_CATS = [[0, '2-5'], [6, '6-9'], [10, '10-12'], [13, '12+']]
