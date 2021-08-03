HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36',
}

CONFIG_URL = 'https://resources.kayosports.com.au/production/ios-android-assets/v2/config/metadata.json'
SPORT_LOGO = 'https://resources.kayosports.com.au/production/sport-logos/1x1/{}.png?imwidth=320'
IMG_URL = 'https://vmndims.kayosports.com.au/api/v2/img/{}'
LICENSE_URL = 'https://drm.streamotion.com.au/licenseServer/widevine/v1/streamotion/license'
CHNO_URL = 'https://i.mjh.nz/Kayo/chnos.json'
CLIENT_ID = 'a0n14xap7jreEXPfLo9F6JLpRp3Xeh2l'
CHANNELS_PANEL = 'A35eyiq8Mm'

FORMAT_HLS_TS = 'hls-ts'
FORMAT_HLS_TS_SSAI = 'ssai-hls-ts'
FORMAT_DASH = 'dash'
FORMAT_DRM_DASH = 'drm-dash'
FORMAT_DRM_DASH_HEVC = 'drm-dash-hevc'
FORMAT_HLS_FMP4 = 'hls-fmp4'
FORMAT_HLS_FMP4_SSAI = 'ssai-hls-fmp4'
CDN_AKAMAI = 'AKAMAI'
CDN_CLOUDFRONT = 'CLOUDFRONT'
CDN_AUTO = 'AUTO'

AVAILABLE_CDNS = [CDN_AKAMAI, CDN_CLOUDFRONT, CDN_AUTO]
SUPPORTED_FORMATS = [FORMAT_HLS_TS_SSAI, FORMAT_HLS_TS, FORMAT_DASH, FORMAT_DRM_DASH, FORMAT_DRM_DASH_HEVC, FORMAT_HLS_FMP4, FORMAT_HLS_FMP4_SSAI]
