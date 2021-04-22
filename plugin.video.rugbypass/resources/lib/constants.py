HEADERS = {
    'User-Agent': 'Mozilla/5.0 (CrKey armv7l 1.5.16041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.0 Safari/537.36',
}

API_URL = 'https://watch.rugbypass.com{}'
IMG_URL = 'https://neulionsmbnyc-a.akamaihd.net/u/mt1/csmrugby/thumbs/{}'

GAMES_EXPIRY    = (60*5) #5 minutes
GAMES_CACHE_KEY = 'games_updated'
SERVICE_TIME    = (GAMES_EXPIRY - 30)