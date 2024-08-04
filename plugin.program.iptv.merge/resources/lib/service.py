from kodi_six import xbmc, xbmcvfs, xbmcaddon
from six.moves.urllib.parse import unquote_plus
from looseversion import LooseVersion

from slyguy import router, gui
from slyguy.util import get_kodi_string, set_kodi_string, kodi_rpc
from slyguy.log import log

from .constants import *
from .merger import check_merge_required
from .settings import settings


def start():
    monitor = xbmc.Monitor()
    restart_queued = False
    just_booted = True

    set_kodi_string('_iptv_merge_service_running', '1')
    set_kodi_string('_iptv_merge_force_run')

    delay = settings.getInt('service_delay', 0)
    if delay:
        log.debug('Service delay: {}s'.format(delay))
        monitor.waitForAbort(delay)

    while not monitor.waitForAbort(1):
        forced = get_kodi_string('_iptv_merge_force_run') or 0
        merge_required = check_merge_required()

        if forced or merge_required:
            set_kodi_string('_iptv_merge_force_run', '1')

            url = router.url_for('run_merge', forced=int(forced))
            _, files = xbmcvfs.listdir(url)
            result, _ = int(files[0][0]), unquote_plus(files[0][1:])
            if result:
                restart_queued = True
            set_kodi_string('_iptv_merge_force_run')

        if just_booted:
            forced = True
            just_booted = False

        if not restart_queued or not settings.getBool('restart_pvr', False):
            continue

        try:
            addon = xbmcaddon.Addon(IPTV_SIMPLE_ID)
            addon_version = LooseVersion(addon.getAddonInfo('version'))
        except Exception as e:
            continue

        if forced:
            progress = gui.progressbg(heading='Reloading IPTV Simple Client')

        if not forced and addon_version >= LooseVersion('20.8.0'):
            log.info('Merge complete. IPTV Simple should reload upaded playlist within 10mins')
            # Do nothing. rely on iptv simple reload every 10mins
            restart_queued = False

        elif LooseVersion('4.3.0') <= addon_version < LooseVersion('20.8.0'):
            # IPTV Simple version 4.3.0 added auto reload on settings change
            log.info('Merge complete. IPTV Simple should reload immediately')
            restart_queued = False
            addon.setSetting('m3uPathType', '0')
            if forced:
                progress.update(100)
                progress.close()

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
