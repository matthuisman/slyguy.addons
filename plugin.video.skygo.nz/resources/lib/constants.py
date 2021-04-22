HEADERS = {
    'User-Agent': 'Mozilla/5.0 (CrKey armv7l 1.5.16041) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.0 Safari/537.36 sky-android (ver=1.0)',
    'sky-x-forwarded-for': 'test',
    'X-Forwarded-For': '202.89.4.222',
}

API_URL           = 'https://www.skygo.co.nz/pro-api{}'
CONTENT_URL       = 'https://www.skygo.co.nz/pub-api/content/v1/'
CHANNELS_URL      = 'https://feed.theplatform.com/f/7tMqSC/O5wnnwnQqDWV?form=json'
IMAGE_URL         = 'https://prod-images.skygo.co.nz/{}'
PLAY_URL          = 'https://feed.theplatform.com/f/7tMqSC/0_V4XPWsMSE9'
WIDEVINE_URL      = 'https://widevine.entitlement.theplatform.com/wv/web/ModularDrm/getWidevineLicense?schema=1.0&token={token}&form=json&account=http://access.auth.theplatform.com/data/Account/2682481291&_releasePid={pid}&_widevineChallenge={challenge}'

OLD_MESSAGE = 'Skygo appears to have switched off their older API this add-on uses.\nThis results in live channels no longer work\nVOD seems to still work.. for now\n\n[B]I have created a new add-on (Sky Go New) based on their new api[/B]\n[B]It is availabe now in the SlyGuy repo[/B]\n\nCurrently it only supports live channels\nBut it has more channels, 2 hour rewind and higher quality!\nVOD and IPTV Merge support should be added to it over the next few weeks'

GENRES = {
    'tvshows': [
        ['All Shows', ''],
        ['Drama', 'drama'],
        ['Kids & Family', 'children'],
        ['Comedy', 'comedy'],
        ['Action', 'action'],
        ['Animated', 'animated'],
        ['Reality', 'reality'],
        ['Documentary', 'documentary'],
        ['Food & Lifestyle', 'lifestyle'],
        ['General Entertainment', 'general_entertainment'],
    ],
    'movies': [
        ['All Movies', ''],
        ['Drama', 'drama'],
        ['Comedy', 'comedy'],
        ['Action', 'action'],
        ['Animated', 'animated'],
        ['Thriller', 'thriller'],
        ['Kids & Family', 'family'],
        ['Documentary/Factual', 'documentary'],
    ],
    'sport': [
        ['All Sports', ''],
        ['Motor Sport', 'motorsport'],
        ['Basketball', 'basketball'],
        ['Golf', 'golf'],
        ['Cricket', 'cricket'],
        ['Rugby', 'rugby'],
        ['League', 'league'],
        ['Football', 'football'],
        ['Netball', 'netball'],
        ['Other', 'other'],
    ],
}
GENRES['boxsets'] = GENRES['tvshows']