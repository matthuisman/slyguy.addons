import json

from kodi_six import xbmc
from threading import Thread

from slyguy.util import get_kodi_string, set_kodi_string
from slyguy.log import log
from slyguy.router import add_url_args
from slyguy.monitor import monitor

class Player(xbmc.Player):
    # def __init__(self, *args, **kwargs):
    #     self._thread = None
    #     self._up_next = None
    #     self._callback = None
    #     super(Player, self).__init__(*args, **kwargs)

    def playback(self):
        play_time = 0
        last_play_time = 0
        last_callback = None

        while not monitor.waitForAbort(1) and self.isPlaying() and self.getPlayingFile() == self._playing_file:
            play_time = int(self.getTime())

            if self._play_skips:
                play_skips = []
                for row in self._play_skips:
                    if play_time >= row['from'] and play_time < row['to']:
                        self.seekTime(row['to'])
                    elif play_time < row['to']:
                        play_skips.append(row)
                self._play_skips = play_skips

            if last_callback is not None:
                if play_time > last_callback:
                    diff = play_time - last_callback
                else:
                    diff = last_callback - play_time

            if self._callback and self._callback['type'] == 'interval' and last_callback != play_time and (last_callback is None or diff >= self._callback['interval']):
                callback = add_url_args(self._callback['callback'], _time=play_time)
                xbmc.executebuiltin('RunPlugin({})'.format(callback))
                last_callback = play_time

        if self._callback and last_callback != play_time:
            # Stop playback callback
            callback = add_url_args(self._callback['callback'], _time=play_time)
            xbmc.executebuiltin('RunPlugin({})'.format(callback))

    def onAVStarted(self):
        self._callback = None
        self._play_skips = []
        self._playing_file = self.getPlayingFile()

        if self.isPlayingVideo():
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        else:
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        play_skips = []
        up_next = get_kodi_string('_slyguy_play_next')
        if up_next:
            set_kodi_string('_slyguy_play_next')
            up_next = json.loads(up_next)
            if up_next['playing_file'] == self._playing_file:
                if up_next['next_file']:
                    self._playlist.remove(up_next['next_file'])
                    self._playlist.add(up_next['next_file'], index=self._playlist.getposition()+1)

                #legacy
                if up_next['time']:
                    play_skips.append({'from': up_next['time'], 'to': 0})

        _skips = get_kodi_string('_slyguy_play_skips')
        if _skips:
            set_kodi_string('_slyguy_play_skips')
            data = json.loads(_skips)
            if data['playing_file'] == self._playing_file:
                play_skips.extend(data['skips'])

        for skip in play_skips:
            if not skip.get('from'):
                continue

            if not skip.get('to'):
                skip['to'] = int(self.getTotalTime())+1
            else:
                skip['to'] -= 3

            self._play_skips.append(skip)

        callback = get_kodi_string('_slyguy_play_callback')
        if callback:
            set_kodi_string('_slyguy_play_callback')
            callback = json.loads(callback)
            if callback['playing_file'] == self._playing_file and callback['callback']:
                self._callback = callback

        if self._callback or self._play_skips:
            self._thread = Thread(target=self.playback)
            self._thread.start()

    # def onPlayBackEnded(self):
    #     vid_playlist   = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    #     music_playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    #     position       = vid_playlist.getposition()+1

    #     if (vid_playlist.size() <= 1 or vid_playlist.size() == position) and (music_playlist.size() <= 1 or music_playlist.size() == position):
    #         self.onPlayBackStopped()

    # def onPlayBackStopped(self):
    #     pass

    # def onPlayBackStarted(self):
    #     pass

    # def onPlayBackPaused(self):
    #     print("AV PAUSED")

    # def onPlayBackResumed(self):
    #     print("AV RESUME")

    # def onPlayBackError(self):
    #     self.onPlayBackStopped()
