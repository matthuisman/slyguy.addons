HEADERS = {
    'user-agent': 'okhttp/4.9.3',
}

AVATAR_URL = 'https://resources.streamotion.com.au/production/binge/profile/avatar-{avatar_id:02d}.png?imwidth=400'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
LIVE_DATA_URL = 'https://i.mjh.nz/Binge/app.json'
EPG_URL = 'https://i.mjh.nz/Binge/epg.xml.gz'
CLIENT_ID = 'QQdtPlVtx1h9BkO09BDM2OrFi5vTPCty'
UDID = 'bc1e95db-723d-48fc-8012-effa322bdbc8'

FORMAT_HLS_TS = 'hls-ts'
FORMAT_DASH = 'dash'
FORMAT_DRM_DASH = 'drm-dash'
FORMAT_HLS_FMP4 = 'hls-fmp4'
CDN_AKAMAI = 'AKAMAI'
CDN_CLOUDFRONT = 'CLOUDFRONT'
CDN_LUMEN = 'LUMEN'
CDN_AUTO = 'AUTO'

AVAILABLE_CDNS = [CDN_AKAMAI, CDN_CLOUDFRONT, CDN_AUTO, CDN_LUMEN]
SUPPORTED_FORMATS = [FORMAT_HLS_TS, FORMAT_DASH, FORMAT_DRM_DASH, FORMAT_HLS_FMP4]
