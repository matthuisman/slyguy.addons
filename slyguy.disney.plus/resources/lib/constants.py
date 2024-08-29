CLIENT_ID = 'disney-svod-3d9324fc'
CLIENT_VERSION = '9.10.0'

API_KEY = 'ZGlzbmV5JmFuZHJvaWQmMS4wLjA.bkeb0m230uUhv8qrAXuNu39tbE_mD5EEhM_NAcohjyA'
CONFIG_URL = 'https://bam-sdk-configs.bamgrid.com/bam-sdk/v5.0/{}/android/v{}/google/tv/prod.json'.format(CLIENT_ID, CLIENT_VERSION)

DEVICE_CODE_URL = 'https://www.disneyplus.com/begin'
PAGE_SIZE_SETS = 15
PAGE_SIZE_CONTENT = 30
SEARCH_QUERY_TYPE = 'ge'
BAM_PARTNER = 'disney'
EXPLORE_VERSION = 'v1.1' #'v1.3' - 1.3 moves a lot more to explore type
 
WATCHLIST_SET_ID = '6f3e3200-ce38-4865-8500-a9f463c1971e'
WATCHLIST_SET_TYPE = 'WatchlistSet'
CONTINUE_WATCHING_SET_ID = '76aed686-1837-49bd-b4f5-5d2a27c0c8d4'
CONTINUE_WATCHING_SET_TYPE = 'ContinueWatchingSet'

HEADERS = {
    'User-Agent': 'BAMSDK/v{} ({} 2.26.2-rc1.0; v5.0/v{}; android; tv)'.format(CLIENT_VERSION, CLIENT_ID, CLIENT_VERSION),
    'x-application-version': 'google',
    'x-bamsdk-platform-id': 'android-tv',
    'x-bamsdk-client-id': CLIENT_ID,
    'x-bamsdk-platform': 'android-tv',
    'x-bamsdk-version': CLIENT_VERSION,
    'Accept-Encoding': 'gzip',
}
