PLAYLIST_FILE_NAME  = 'playlist.m3u8'
EPG_FILE_NAME       = 'epg.xml'
IPTV_SIMPLE_ID      = 'pvr.iptvsimple'
METHOD_PLAYLIST     = 'playlist'
METHOD_EPG          = 'epg'
MERGE_SETTING_FILE  = '.iptv_merge'

INTEGRATIONS = {
    'plugin.video.iptvsimple.addons': {
        'min_version': '0.0.7',
        'playlist': 'special://profile/addon_data/$ID/streams.m3u8',
        'epg': 'special://profile/addon_data/$ID/xmltv.xml',
    },
    'plugin.video.sling': {
        'min_version': '0.0.103',
        'playlist': 'http://127.0.0.1:9999/channels.m3u',
        'epg': 'http://127.0.0.1:9999/guide.xml',
        'settings': {
            'Use_Slinger': 'true',
            'Enable_EPG': 'false',
        }
    },
    'service.iptv.manager': {
        'min_version': '0.2.1',
        'playlist': 'special://profile/addon_data/$ID/playlist.m3u8',
        'epg': 'special://profile/addon_data/$ID/epg.xml',
        'settings': {
            'iptv_simple_restart': 'false',
        }
    },
}
