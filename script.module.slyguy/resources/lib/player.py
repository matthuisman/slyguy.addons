import json
import time

from kodi_six import xbmc
from threading import Thread

from slyguy.util import get_kodi_string, set_kodi_string
from slyguy.log import log
from slyguy.router import add_url_args

from .monitor import monitor

class Player(xbmc.Player):
    # def __init__(self, *args, **kwargs):
    #     self._thread = None
    #     self._up_next = None
    #     self._callback = None
    #     super(Player, self).__init__(*args, **kwargs)

    def playback(self, playing_file):
        last_callback = None
        cur_time = time.time()
        play_time = 0

        while not monitor.waitForAbort(1) and self.isPlaying() and self.getPlayingFile() == playing_file:
            cur_time  = time.time()
            play_time = self.getTime()

            play_skips = []
            for row in self._play_skips:
                if play_time >= row['from']:
                    self.seekTime(row['to'])
                else:
                    play_skips.append(row)

            self._play_skips = play_skips

            if self._up_next and play_time >= self._up_next['time']:
                play_time = self.getTotalTime()
                self.seekTime(play_time)
                last_callback = None

            if self._callback and self._callback['type'] == 'interval' and (not last_callback or cur_time >= last_callback + self._callback['interval']):
                callback = add_url_args(self._callback['callback'], _time=int(play_time))
                xbmc.executebuiltin('RunPlugin({})'.format(callback))
                last_callback = cur_time

        if self._callback:
            callback = add_url_args(self._callback['callback'], _time=int(play_time))
            xbmc.executebuiltin('RunPlugin({})'.format(callback))

    def onAVStarted(self):
        self._up_next = None
        self._callback = None
        self._playlist = None
        self._play_skips = None

        if self.isPlayingVideo():
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        else:
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        up_next = get_kodi_string('_slyguy_play_next')
        if up_next:
            set_kodi_string('_slyguy_play_next')
            up_next = json.loads(up_next)
            if up_next['playing_file'] == self.getPlayingFile():
                if up_next['next_file']:
                    self._playlist.remove(up_next['next_file'])
                    self._playlist.add(up_next['next_file'], index=self._playlist.getposition()+1)

                if up_next['time']:
                    self._up_next = up_next

        play_skips = get_kodi_string('_slyguy_play_skips')
        if play_skips:
            set_kodi_string('_slyguy_play_skips')
            play_skips = json.loads(play_skips)
            if play_skips['playing_file'] == self.getPlayingFile():
                self._play_skips = play_skips['skips']

        callback = get_kodi_string('_slyguy_play_callback')
        if callback:
            set_kodi_string('_slyguy_play_callback')
            callback = json.loads(callback)
            if callback['playing_file'] == self.getPlayingFile() and callback['callback']:
                self._callback = callback

        if self._up_next or self._callback or self._play_skips:
            self._thread = Thread(target=self.playback, args=(self.getPlayingFile(),))
            self._thread.start()

    # def onPlayBackEnded(self):
    #     vid_playlist   = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    #     music_playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    #     position       = vid_playlist.getposition()+1

    #     if (vid_playlist.size() <= 1 or vid_playlist.size() == position) and (music_playlist.size() <= 1 or music_playlist.size() == position):
    #         self.onPlayBackStopped()

    # def onPlayBackStopped(self):
    #     set_kodi_string('_slyguy_last_quality')

    # def onPlayBackStarted(self):
    #     pass

    # def onPlayBackPaused(self):
    #     print("AV PAUSED")

    # def onPlayBackResumed(self):
    #     print("AV RESUME")

    # def onPlayBackError(self):
    #     self.onPlayBackStopped()
