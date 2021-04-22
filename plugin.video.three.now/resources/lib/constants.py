HEADERS    = {
    'User-Agent': 'Mozilla/5.0 (CrKey armv7l 1.5.16041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.0 Safari/537.36',
    'X-Forwarded-For': '202.89.4.222',
}

API_URL = 'https://now-api4-prod.fullscreen.nz/v4/{}'

SHOWS_EXPIRY        = (60*60*24) #24 Hours
LIVE_EXPIRY         = (60*60*24) #24 Hours
EPISODE_EXPIRY      = (60*5)     #5 Minutes
SHOWS_CACHE_KEY     = 'shows'
LIVE_CACHE_KEY      = 'live'

SEARCH_MATCH_RATIO = 0.75

BRIGHTCOVE_URL     = 'https://edge.api.brightcove.com/playback/v1/accounts/{}/videos/{}'
BRIGHTCOVE_KEY     = 'BCpkADawqM2NDYVFYXV66rIDrq6i9YpFSTom-hlJ_pdoGkeWuItRDsn1Bhm7QVyQvFIF0OExqoywBvX5-aAFaxYHPlq9st-1mQ73ZONxFHTx0N7opvkHJYpbd_Hi1gJuPP5qCFxyxB8oevg-'
BRIGHTCOVE_ACCOUNT = '3812193411001'