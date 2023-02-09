HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
}

API_URL = 'https://api.kayosports.com.au/v3{}'
AUTH_URL = 'https://auth.streamotion.com.au/oauth'
PROFILE_URL = 'https://profileapi.streamotion.com.au'
RESOURCE_URL = 'https://resources.kayosports.com.au'
CDN_URL = 'https://cdnselectionserviceapi.kayosports.com.au'
PLAY_URL = 'https://play.kayosports.com.au/api/v2'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
LIVE_DATA_URL = 'https://i.mjh.nz/Kayo/app.json'
EPG_URL = 'https://i.mjh.nz/Kayo/epg.xml.gz'
CLIENT_ID = 'a0n14xap7jreEXPfLo9F6JLpRp3Xeh2l'
UDID = 'bc1e95db-723d-48fc-8012-effa322bdbc8'

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
