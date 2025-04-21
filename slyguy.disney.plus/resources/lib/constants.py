CLIENT_ID = 'disney-svod-3d9324fc'
CLIENT_VERSION = '9.10.0'

API_KEY = 'ZGlzbmV5JmFuZHJvaWQmMS4wLjA.bkeb0m230uUhv8qrAXuNu39tbE_mD5EEhM_NAcohjyA'
CONFIG_URL = 'https://bam-sdk-configs.bamgrid.com/bam-sdk/v5.0/{}/android/v{}/google/tv/prod.json'.format(CLIENT_ID, CLIENT_VERSION)

DEVICE_CODE_URL = 'https://www.disneyplus.com/begin'
PAGE_SIZE_SETS = 15
PAGE_SIZE_CONTENT = 30
SEARCH_QUERY_TYPE = 'ge'
BAM_PARTNER = 'disney'
EXPLORE_VERSION = 'v1.9'

SUGGESTED_ID = '3cd8f37d-5480-46fb-9eeb-5002123abe53'
EXTRAS_ID = '83f33e19-3e08-490d-a59a-6ef5cb93f030'

EPISODES = 'EPISODES'
SUGGESTED = 'SUGGESTED'
EXTRAS = 'EXTRAS'
DETAILS = 'DETAILS'
BROWSE = 'BROWSE'
PLAYBACK = 'PLAYBACK'
TRAILER = 'TRAILER'
MODIFYSAVES = 'MODIFYSAVES'
REMOVECONTINUEWATCHING = 'REMOVECONTINUEWATCHING'
MODAL = 'MODAL'
CONTAINERS = 'CONTAINERS'
ACTIONS = 'ACTIONS'

HEADERS = {
    'User-Agent': 'BAMSDK/v{} ({} 2.26.2-rc1.0; v5.0/v{}; android; tv)'.format(CLIENT_VERSION, CLIENT_ID, CLIENT_VERSION),
    'x-application-version': 'google',
    'x-bamsdk-platform-id': 'android-tv',
    'x-bamsdk-client-id': CLIENT_ID,
    'x-bamsdk-platform': 'android-tv',
    'x-bamsdk-version': CLIENT_VERSION,
    'Accept-Encoding': 'gzip',
}
