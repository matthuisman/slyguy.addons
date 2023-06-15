from slyguy import inputstream
from slyguy.util import get_addon

INPUTSTREAM_PROTOCOLS = {
    'mpd': 'inputstream.adaptive',
    'ism': 'inputstream.adaptive',
    'hls': 'inputstream.adaptive',
    'rtmp': 'inputstream.rtmp'
}

class Helper:
    def __init__(self, protocol, drm=None):
        protocol = str(protocol).lower().strip()
        drm = str(drm).lower()

        self.inputstream_addon = INPUTSTREAM_PROTOCOLS[protocol]

        if protocol == 'ism':
            self.ia = inputstream.Playready()
        elif 'widevine' in drm:
            self.ia = inputstream.Widevine()
            if protocol == 'hls':
                self.ia.manifest_type = 'hls'
                self.ia.mimetype = 'application/vnd.apple.mpegurl'
        elif protocol == 'mpd':
            self.ia = inputstream.MPD()
        elif protocol == 'hls':
            self.ia = inputstream.HLS()
        else:
            self.ia = None

    def check_inputstream(self):
        if self.ia is None:
            return get_addon(self.inputstream_addon) is not None

        return self.ia.check()
