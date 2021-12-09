HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
}

AVATAR_URL = 'https://resources.streamotion.com.au/production/binge/profile/avatar-{avatar_id:02d}.png?imwidth=400'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
LIVE_DATA_URL = 'https://i.mjh.nz/Binge/app.json'
EPG_URL = 'https://i.mjh.nz/Binge/epg.xml.gz'
CLIENT_ID = 'QQdtPlVtx1h9BkO09BDM2OrFi5vTPCty'
UDID = 'bc1e95db-723d-48fc-8012-effa322bdbc8'

FORMAT_HLS_TS = 'hls-ts'
FORMAT_DASH = 'dash'
FORMAT_HLS_FMP4 = 'hls-fmp4'
FORMAT_DRM_DASH = 'drm-dash'
FORMAT_DRM_DASH_HEVC = 'drm-dash-hevc'
PROVIDER_AKAMAI = 'AKAMAI'
PROVIDER_CLOUDFRONT = 'CLOUDFRONT'

SUPPORTED_PROVIDERS = [PROVIDER_AKAMAI, PROVIDER_CLOUDFRONT]
SUPPORTED_FORMATS = [FORMAT_HLS_TS, FORMAT_DASH, FORMAT_HLS_FMP4, FORMAT_DRM_DASH, FORMAT_DRM_DASH_HEVC]
