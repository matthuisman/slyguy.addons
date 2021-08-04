import time

from kodi_six import xbmc, xbmcvfs, xbmcaddon
from six.moves.urllib.parse import unquote_plus

from slyguy import router, settings, userdata, gui
from slyguy.constants import KODI_VERSION
from slyguy.util import get_kodi_string, set_kodi_string, kodi_rpc, kodi_db
from slyguy.log import log

from .constants import *

from .http import HTTP

def start():
    http = HTTP()

    monitor = xbmc.Monitor()
    restart_queued = False

    boot_merge = settings.getBool('boot_merge', False)
    set_kodi_string('_iptv_merge_force_run')

    while not monitor.waitForAbort(1):
        http.start() if settings.getBool('http_api', False) else http.stop()

        forced = get_kodi_string('_iptv_merge_force_run') or 0

        if forced or boot_merge or (settings.getBool('auto_merge', True) and time.time() - userdata.get('last_run', 0) > settings.getInt('reload_time_hours', 12) * 3600):
            set_kodi_string('_iptv_merge_force_run', '1')

            url = router.url_for('run_merge', forced=int(forced))
            dirs, files = xbmcvfs.listdir(url)
            result, msg = int(files[0][0]), unquote_plus(files[0][1:])
            if result:
                restart_queued = True

            userdata.set('last_run', int(time.time()))
            set_kodi_string('_iptv_merge_force_run')

        if restart_queued and settings.getBool('restart_pvr', False):
            if forced: progress = gui.progressbg(heading='Reloading IPTV Simple Client')

            if KODI_VERSION > 18:
                restart_queued = False
                try: xbmcaddon.Addon(IPTV_SIMPLE_ID).setSetting('m3uPathType', '0')
                except Exception as e: pass

            elif forced or (not xbmc.getCondVisibility('Pvr.IsPlayingTv') and not xbmc.getCondVisibility('Pvr.IsPlayingRadio')):
                restart_queued = False
                kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': False})

                wait_delay = 4
                for i in range(wait_delay):
                    if monitor.waitForAbort(1):
                        break
                    if forced: progress.update((i+1)*int(100/wait_delay))

                kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': True})

            if forced:
                progress.update(100)
                progress.close()

        boot_merge = False

    http.stop()
