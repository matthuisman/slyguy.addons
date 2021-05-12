HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
}

EPG_URL  = 'https://service-channels.clusters.pluto.tv/v1/guide'
PLAY_URL = 'https://service-stitcher.clusters.pluto.tv/stitch/hls/channel/{id}/master.m3u8?advertisingId=&appName=web&appVersion=5.16.0-d477896b413cece569cca008ddae951d02cadc9e&app_name=web&clientDeviceType=0&clientID=%7Bdevice_id%7D&clientModelNumber=na&deviceDNT=false&deviceId=%7Bdevice_id%7D&deviceLat=34.0485&deviceLon=-118.2529&deviceMake=Chrome&deviceModel=web&deviceType=web&deviceVersion=90.0.4430.212&marketingRegion=US&serverSideAds=true&sessionID=%7Bsid%7D&sid=%7Bsid%7D&userId='
LOGO_URL = 'https://images.pluto.tv/channels/{id}/colorLogoPNG.png'

MH_DATA_URL = 'https://i.mjh.nz/PlutoTV/{region}.json.gz'
MH_EPG_URL  = 'https://i.mjh.nz/PlutoTV/{region}.xml.gz'

PLUTO_PARAMS = {
    'deviceId': '6fbead95-26b1-415d-998f-1bdef62d10be',
    'deviceMake': 'Chrome',
    'deviceType': 'web',
    'deviceVersion': '88.0.4324.150',
    'deviceModel': 'web',
    'DNT': '0',
    'appName': 'web',
    'appVersion': '5.14.0-0f5ca04c21649b8c8aad4e56266a23b96d73b83a',
    'serverSideAds': 'false',
    'channelSlug': '',
    'episodeSlugs': '',
    'channelID': '',
    'clientID': '6fbead95-26b1-415d-998f-1bdef62d10be',
    'clientModelNumber': 'na',
}

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