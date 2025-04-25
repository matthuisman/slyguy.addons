HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
}

DEVICE_ACTIVATE_URL = 'https://hulu.com/activate'
API_URL = 'https://discover.hulu.com{}'

# this is old device that returns 4K MPD:
# https://vodmanifest.hulustream.com
# newer devices return 2K MPD:
# https://dynamic-manifest.hulustream.com
DEEJAY_DEVICE_ID = 189
DEEJAY_KEY_VERSION = 8
