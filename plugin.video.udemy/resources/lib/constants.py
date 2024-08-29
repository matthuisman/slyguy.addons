HEADERS = {
    'User-Agent': 'okhttp/3.12.1',
    'Authorization': 'Basic YWQxMmVjYTljYmUxN2FmYWM2MjU5ZmU1ZDk4NDcxYTY6YTdjNjMwNjQ2MzA4ODI0YjIzMDFmZGI2MGVjZmQ4YTA5NDdlODJkNQ==',
}

CLIENT_ID = 'bd2565cb7b0c313f5e9bae44961e8db2'
DEFAULT_HOST = 'www.udemy.com'
API_URL = 'https://{}/api-2.0/{{}}'
PAGE_SIZE = 10
MAX_PAGE_SIZE = 1400
WV_URL = 'https://www.udemy.com/api-2.0/media-license-server/validate-auth-token?drm_type=widevine&auth_token={token}'

BANDWIDTH_MAP = {
    1080: [5000000, '1920x1080'],
    720: [2500000, '1280x720'],
    480: [1300000, '854x480'],
    360: [660000, '640x360'],
    144: [190000, '256x144'],
}
