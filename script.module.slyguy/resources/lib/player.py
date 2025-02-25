import json
import time

from kodi_six import xbmc
from threading import Thread

from slyguy.log import log
from slyguy.util import get_kodi_string, set_kodi_string
from slyguy.router import add_url_args
from slyguy.monitor import monitor


class Player(xbmc.Player):
    def playback(self, playing_file, callback, play_skips):
        play_time = 0
        last_play_time = int(self.getTime())
        last_callback = None
        last_callback_ts = int(time.time())

        while not monitor.waitForAbort(1) and self.isPlaying() and self.getPlayingFile() == playing_file:
            if callback and callback['type'] == 'interval_ts' and int(time.time()) - last_callback_ts >= callback['interval']:
                plugin_url = add_url_args(callback['callback'], _time=play_time)
                log.debug("Player callback: {}".format(plugin_url))
                xbmc.executebuiltin('RunPlugin({})'.format(plugin_url))
                last_callback_ts = int(time.time())

            play_time = int(self.getTime())

            diff = abs(play_time - last_play_time)
            last_play_time = play_time

            if diff > 5:
                #we are jumping around
                continue

            new_play_skips = []
            for row in play_skips:
                if play_time >= row['to']:
                    continue

                diff = play_time - row['from']
                if diff < 0:
                    new_play_skips.append(row)
                elif diff <= 5:
                    self.seek(row['to'])
            play_skips = new_play_skips

            diff = 0
            if last_callback is not None:
                diff = abs(play_time - last_callback)

            if callback and callback['type'] == 'interval' and last_callback != play_time and (last_callback is None or diff >= callback['interval']):
                plugin_url = add_url_args(callback['callback'], _time=play_time)
                log.debug("Player callback: {}".format(plugin_url))
                xbmc.executebuiltin('RunPlugin({})'.format(plugin_url))
                last_callback = play_time

        log.debug("Playback finished at {}s".format(play_time))
        if callback and last_callback != play_time:
            # Stop playback callback
            plugin_url = add_url_args(callback['callback'], _time=play_time)
            log.debug("Player callback: {}".format(plugin_url))
            xbmc.executebuiltin('RunPlugin({})'.format(plugin_url))

    def seek(self, seconds):
        # TODO: doesnt seem to mark as watched. try using API seek instead
        log.debug("Seeking to: {}".format(seconds))
        self.seekTime(seconds)

    def onAVStarted(self):
        try:
            play_data = json.loads(get_kodi_string('_slyguy_play_data'))
        except:
            return

        set_kodi_string('_slyguy_play_data')
        playing_file = self.getPlayingFile()
        if play_data['playing_file'] != playing_file:
            return

        if self.isPlayingVideo():
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        else:
            playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        if play_data['next']['next_file']:
            pos = playlist.getposition()+1
            if playlist.size() > pos and playlist[pos].getPath() == play_data['next']['next_file']:
                log.debug('Up next already correct: {}'.format(play_data['next']['next_file']))
            else:
                playlist.remove(play_data['next']['next_file'])
                playlist.add(play_data['next']['next_file'], index=playlist.getposition()+1)
                log.debug('Up next added: {}'.format(play_data['next']['next_file']))

        play_skips = []
        for skip in play_data['skips']:
            if not skip.get('to'):
                skip['to'] = int(self.getTotalTime())+1
            else:
                if skip['to'] < 0:
                    self.seek(self.getTotalTime() + skip['to'] - 3)
                    continue

                skip['to'] -= 3

            if not skip.get('from'):
                continue

            play_skips.append(skip)

        callback = None
        if play_data['callback']['callback']:
            callback = play_data['callback']

        if callback or play_skips:
            self._thread = Thread(target=self.playback, args=(playing_file, callback, play_skips), daemon=True)
            self._thread.start()
