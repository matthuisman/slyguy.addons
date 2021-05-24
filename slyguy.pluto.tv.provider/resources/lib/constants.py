HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
}

EPG_URL  = 'https://service-channels.clusters.pluto.tv/v1/guide'
PLAY_URL = 'https://service-stitcher.clusters.pluto.tv/v1/stitch/embed/hls/channel/{id}/master.m3u8?deviceId=channel&deviceModel=web&deviceVersion=1.0&appVersion=1.0&deviceType=rokuChannel&deviceMake=rokuChannel&deviceDNT=1&advertisingId=channel&embedPartner=rokuChannel&appName=rokuchannel&is_lat=1&bmodel=bm1&content=channel&platform=web&tags=ROKU_CONTENT_TAGS&coppa=false&content_type=livefeed&rdid=channel&genre=ROKU_ADS_CONTENT_GENRE&content_rating=ROKU_ADS_CONTENT_RATING&studio_id=viacom&channel_id=channel'
ALT_URL  = 'https://service-stitcher.clusters.pluto.tv/stitch/hls/channel/{id}/master.m3u8?{params}'
LOGO_URL = 'https://images.pluto.tv/channels/{id}/colorLogoPNG.png'

MH_DATA_URL = 'https://i.mjh.nz/PlutoTV/{region}.json.gz'
MH_EPG_URL  = 'https://i.mjh.nz/PlutoTV/{region}.xml.gz'

US = 'us'
UK = 'uk'
DE = 'de'
ES = 'es'
CA = 'ca'
BR = 'br'
MX = 'mx'
FR = 'fr'
ALL = 'all'
LOCAL = 'local'
CUSTOM = 'custom'

X_FORWARDS = {
    US: '185.236.200.172',
    UK: '185.86.151.11',
    DE: '85.214.132.117',
    ES: '88.26.241.248',
    CA: '192.206.151.131',
    BR: '177.47.27.205',
    MX: '200.68.128.83',
    FR: '176.31.84.249',
}

X_FORWARDS[ALL] = X_FORWARDS[US]

REGIONS = [US, UK, LOCAL, CUSTOM, DE, ES, CA, ALL, BR, MX, FR]