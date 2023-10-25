from kodi_six import xbmcvfs, xbmcaddon, xbmc

INPUTSTREAM_PROTOCOLS = {
    'mpd': 'inputstream.adaptive',
    'ism': 'inputstream.adaptive',
    'hls': 'inputstream.adaptive',
    'rtmp': 'inputstream.rtmp'
}

class Helper:
    def __init__(self, protocol, drm=None):
        self.protocol = str(protocol).lower().strip()
        self.drm = str(drm or '').lower().strip()
        self.inputstream_addon = INPUTSTREAM_PROTOCOLS[protocol]

    def check_inputstream(self):
        if xbmcaddon.Addon('script.module.inputstreamhelper').getSetting('skip_check').lower() == 'true':
            xbmc.log('Skipping Inputstream check')
            return True

        xbmc.log('Running Slyguy DRM Helper')
        _, files = xbmcvfs.listdir('plugin://script.module.slyguy/?_=_ia_helper&protocol={}&drm={}'.format(self.protocol, self.drm))
        result = bool(files and files[0].lower() == 'true')
        xbmc.log('Slyguy DRM Helper Result: {}'.format(result))
        return result
