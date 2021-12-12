PLAYLIST_FILE_NAME  = 'playlist.m3u8'
EPG_FILE_NAME = 'epg.xml'
IPTV_SIMPLE_ID = 'pvr.iptvsimple'
METHOD_PLAYLIST = 'playlist'
METHOD_EPG = 'epg'
MERGE_SETTING_FILE = '.iptv_merge'

TYPE_IPTV_MERGE = 1
TYPE_IPTV_MANAGER = 2
TYPE_INTEGRATION = 3

DEFAULT_USERAGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

INTEGRATIONS = {
    'plugin.video.jiotv': {
        'min_version': '2.0.14',
        'playlist': 'special://profile/addon_data/$ID/playlist.m3u',
        'settings': {
            'm3ugen': 'true',
        },
    },
    'plugin.video.iptvsimple.addons': {
        'min_version': '0.0.7',
        'playlist': 'special://profile/addon_data/$ID/streams.m3u8',
        'epg': 'special://profile/addon_data/$ID/xmltv.xml',
    },
    'plugin.video.sling': {
        'min_version': '2021.5.4.1',
        'playlist': 'http://127.0.0.1:9999/channels.m3u',
        'epg': 'http://127.0.0.1:9999/guide.xml',
        'settings': {
            'Use_Slinger': 'true',
            'Enable_EPG': 'false',
            'Run_Updates': 'true',
            'Update_Channels': 'true',
            'Update_Guide': 'true',
        },
    },
    'plugin.video.pseudotv.live': {
        'min_version': '0.2.9',
        'playlist': 'special://profile/addon_data/$ID/pseudotv.m3u',
        'epg': 'special://profile/addon_data/$ID/pseudotv.xml',
        # 'genres': 'special://profile/addon_data/$ID/genres.xml',
        # 'logos': 'special://profile/addon_data/$ID/cache/logos',
        'settings': {
            'User_Folder': 'special://profile/addon_data/$ID/',
        },
    },
}
