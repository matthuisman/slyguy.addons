CLIENT_ID = 'star-22bcaf0a'
CLIENT_VERSION = '6.5.0' #6.1.0

API_VERSION = '5.1'
API_KEY = 'c3RhciZicm93c2VyJjEuMC4w.COknIGCR7I6N0M5PGnlcdbESHGkNv7POwhFNL-_vIdg'
CONFIG_URL = 'https://bam-sdk-configs.bamgrid.com/bam-sdk/v3.0/{}/android/v{}/google/tv/prod.json'.format(CLIENT_ID, CLIENT_VERSION)
PAGE_SIZE_SETS = 15
PAGE_SIZE_CONTENT = 30
SEARCH_QUERY_TYPE = 'ge'
BAM_PARTNER = 'star'

WATCHLIST_SET_ID = 'f8085c31-cdd0-4429-9a29-f70ad0f3f84e'
WATCHLIST_SET_TYPE = 'WatchlistSet'
CONTINUE_WATCHING_SET_ID = 'c1293079-2835-40c3-a062-2de6fd1dc58c'
CONTINUE_WATCHING_SET_TYPE = 'ContinueWatchingSet'

HEADERS = {
    'User-Agent': 'BAMSDK/v{} ({} 1.16.0.0; v3.0/v{}; android; tv)'.format(CLIENT_VERSION, CLIENT_ID, CLIENT_VERSION),
    'x-application-version': 'google',
    'x-bamsdk-platform-id': 'android-tv',
    'x-bamsdk-client-id': CLIENT_ID,
    'x-bamsdk-platform': 'android-tv',
    'x-bamsdk-version': CLIENT_VERSION,
    'Accept-Encoding': 'gzip',
}

RATIO_ASK = 0
RATIO_IMAX = 1
RATIO_WIDESCREEN = 2
RATIO_TYPES = [RATIO_ASK, RATIO_IMAX, RATIO_WIDESCREEN]
