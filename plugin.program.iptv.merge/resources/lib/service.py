import time
from distutils.version import LooseVersion

from kodi_six import xbmc, xbmcvfs, xbmcaddon
from six.moves.urllib.parse import unquote_plus

import arrow

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

    delay = settings.getInt('service_delay', 0)
    if delay:
        log.debug('Service delay: {}s'.format(delay))
        monitor.waitForAbort(delay)

    count = 30
    while not monitor.waitForAbort(1):
        count += 1

        forced = get_kodi_string('_iptv_merge_force_run') or 0
        reload_time_hours = False
        merge_at_hour = False

        if count >= 30:
            count = 0
            http.start() if settings.getBool('http_api', False) else http.stop()

            reload_time_hours = settings.getBool('auto_merge', True)
            if reload_time_hours:
                reload_time_hours = time.time() - userdata.get('last_run', 0) > settings.getInt('reload_time_hours', 12) * 3600

            merge_at_hour = not reload_time_hours and settings.getBool('merge_at_hour', True)
            if merge_at_hour:
                now = arrow.now()
                run_ts = now.replace(hour=int(settings.getInt('merge_hour', 3)), minute=0, second=0, microsecond=0).timestamp
                merge_at_hour = userdata.get('last_run', 0) < run_ts and now.timestamp >= run_ts

        if forced or boot_merge or reload_time_hours or merge_at_hour:
            set_kodi_string('_iptv_merge_force_run', '1')

            url = router.url_for('run_merge', forced=int(forced))
            dirs, files = xbmcvfs.listdir(url)
            result, msg = int(files[0][0]), unquote_plus(files[0][1:])
            if result:
                restart_queued = True

            if reload_time_hours or merge_at_hour:
                userdata.set('last_run', int(time.time()))
            set_kodi_string('_iptv_merge_force_run')

        if restart_queued and settings.getBool('restart_pvr', False):
            if forced: progress = gui.progressbg(heading='Reloading IPTV Simple Client')

            try:
                addon = xbmcaddon.Addon(IPTV_SIMPLE_ID)
                addon_version = LooseVersion(addon.getAddonInfo('version'))
            except Exception as e:
                addon = None

            # if addon and not forced and addon_version >= LooseVersion('20.8.0'):
            #     log.info('Merge complete. IPTV Simple should reload upaded playlist within 10mins')
            #     # Do nothing. rely on iptv simple reload every 10mins as we can't set settings on multi-instance yet
            #     restart_queued = False

            if addon and LooseVersion('4.3.0') <= addon_version < LooseVersion('20.8.0'):
                # IPTV Simple version 4.3.0 added auto reload on settings change
                log.info('Merge complete. IPTV Simple should reload immediately')
                restart_queued = False
                addon.setSetting('m3uPathType', '0')

            elif forced or (not xbmc.getCondVisibility('Pvr.IsPlayingTv') and not xbmc.getCondVisibility('Pvr.IsPlayingRadio')):
                restart_queued = False
                log.info('Merge complete. Reloading IPTV Simple using legacy enable/disable method')
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
