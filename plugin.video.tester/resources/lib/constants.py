VIDEO_TESTS = [
    {
        'name': 'HLS',
        'type': 'std',
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8',
    },
    {
        'name': 'InputStream Adaptive - HLS',
        'type': 'ia_hls',
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8',
    },
    # {
    #     'name': 'InputStream Adaptive - HLS with Widevine',
    #     'type': 'ia_widevine_hls',
    #     'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion_drm/m3u8s/11331.m3u8',
    #     'license_key': 'https://cwip-shaka-proxy.appspot.com/no_auth',
    # },
    {
        'name': 'InputStream Adaptive - Dash',
        'type': 'ia_mpd',
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd',
    },
    {
        'name': 'InputStream Adaptive - Dash with Widevine',
        'type': 'ia_widevine',
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion_drm/mpds/11331.mpd',
        'license_key': 'https://cwip-shaka-proxy.appspot.com/no_auth',
    },
]