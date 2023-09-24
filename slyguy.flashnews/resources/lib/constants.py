HEADERS = {
    'User-Agent': 'okhttp/4.9.3',
    'Accept': '',
    'Accept-Charset': '',
}

PLAY_HEADERS = {
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; SHIELD Android TV Build/PPR1.180610.011)',
    'Accept': '',
    'Accept-Charset': '',
}

AVATAR_URL = 'https://resources.streamotion.com.au/production/flash/profile/avatar-{avatar_id:02d}.png?imwidth=400'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
LIVE_DATA_URL = 'https://i.mjh.nz/Flash/app.json.gz'
EPG_URL = 'https://i.mjh.nz/Flash/epg.xml.gz'
CLIENT_ID = 'C6eoEMBGpDRnuDaTqRt6KJLdxXvXUuaG'
UDID = 'bc1e95db-723d-48fc-8012-effa322bdbc8'
CODE_URL = 'flashnews.com.au/connect'

FORMAT_HLS_TS = 'hls-ts'
FORMAT_HLS_TS_SSAI = 'ssai-hls-ts'
FORMAT_DASH = 'dash'
FORMAT_DRM_DASH = 'drm-dash'
FORMAT_DRM_DASH_HEVC = 'drm-dash-hevc'
FORMAT_HLS_FMP4 = 'hls-fmp4'
FORMAT_HLS_FMP4_SSAI = 'ssai-hls-fmp4'
CDN_AKAMAI = 'AKAMAI'
CDN_CLOUDFRONT = 'CLOUDFRONT'
CDN_LUMEN = 'LUMEN'
CDN_AUTO = 'AUTO'

AVAILABLE_CDNS = [CDN_AKAMAI, CDN_CLOUDFRONT, CDN_AUTO, CDN_LUMEN]
SUPPORTED_FORMATS = [FORMAT_HLS_TS, FORMAT_DASH, FORMAT_DRM_DASH, FORMAT_DRM_DASH_HEVC, FORMAT_HLS_TS_SSAI, FORMAT_HLS_FMP4, FORMAT_HLS_FMP4_SSAI]
