import json
import time

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
        last_play_time = int(self.getTime())
        last_callback = None
        last_callback_ts = int(time.time())

        while not monitor.waitForAbort(1) and self.isPlaying() and self.getPlayingFile() == self._playing_file:
            if self._callback and self._callback['type'] == 'interval_ts' and int(time.time()) - last_callback_ts >= self._callback['interval']:
                callback = add_url_args(self._callback['callback'], _time=play_time)
                xbmc.executebuiltin('RunPlugin({})'.format(callback))
                last_callback_ts = int(time.time())

            play_time = int(self.getTime())

            diff = abs(play_time - last_play_time)
            last_play_time = play_time

            if diff > 5:
                #we are jumping around
                continue

            play_skips = []
            for row in self._play_skips:
                if play_time >= row['to']:
                    continue

                diff = play_time - row['from']
                if diff < 0:
                    play_skips.append(row)
                elif diff <= 5:
                    self.seekTime(row['to'])
            self._play_skips = play_skips

            diff = 0
            if last_callback is not None:
                diff = abs(play_time - last_callback)

            if self._callback and self._callback['type'] == 'interval' and last_callback != play_time and (last_callback is None or diff >= self._callback['interval']):
                callback = add_url_args(self._callback['callback'], _time=play_time)
                xbmc.executebuiltin('RunPlugin({})'.format(callback))
                last_callback = play_time

        if self._callback and last_callback != play_time:
            # Stop playback callback
            callback = add_url_args(self._callback['callback'], _time=play_time)
            xbmc.executebuiltin('RunPlugin({})'.format(callback))

    def onAVStarted(self):
        try:
            play_data = json.loads(get_kodi_string('_slyguy_play_data'))
        except:
            return

        set_kodi_string('_slyguy_play_data')

        self._callback = None
        self._play_skips = []
        self._playing_file = self.getPlayingFile()

        if play_data['playing_file'] != self._playing_file:
            return

        if self.isPlayingVideo():
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        else:
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        play_skips = play_data['skips']

        if play_data['next']['next_file']:
            self._playlist.remove(play_data['next']['next_file'])
            self._playlist.add(play_data['next']['next_file'], index=self._playlist.getposition()+1)

        #legacy
        if play_data['next']['time']:
            play_skips.append({'from': play_data['next']['time'], 'to': 0})

        for skip in play_skips:
            if not skip.get('to'):
                skip['to'] = int(self.getTotalTime())+1
            else:
                if skip['to'] < 0:
                    self.seekTime(self.getTotalTime() + skip['to'] - 3)
                    continue

                skip['to'] -= 3

            if not skip.get('from'):
                continue

            self._play_skips.append(skip)

        ## Workaround for suspect IA bug: https://github.com/xbmc/inputstream.adaptive/issues/821
        # if int(self.getTime()) < 0:
        #     self.seekTime(0)

        if play_data['callback']['callback']:
            self._callback = play_data['callback']

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
