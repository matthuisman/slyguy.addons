VIDEO_TESTS = [
    {
        'name': 'HLS',
        'type': 'std',
        'url': 'https://bitmovin-a.akamaihd.net/content/MI201109210084_1/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8',
    },
    {
        'name': 'InputStream Adaptive - HLS',
        'type': 'ia_hls',
        'url': 'https://bitmovin-a.akamaihd.net/content/MI201109210084_1/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8',
    },
    {
        'name': 'InputStream Adaptive - Dash',
        'type': 'ia_mpd',
        'url': 'https://bitmovin-a.akamaihd.net/content/MI201109210084_1/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd',
    },
    {
        'name': 'InputStream Adaptive - Dash with Widevine',
        'type': 'ia_widevine',
        'url': 'https://bitmovin-a.akamaihd.net/content/art-of-motion_drm/mpds/11331.mpd',
        'license_key': 'https://cwip-shaka-proxy.appspot.com/no_auth',
    },
]