import time
import sqlite3

from kodi_six import xbmc, xbmcvfs, xbmcaddon
from six.moves.urllib.parse import unquote

from slyguy import router, settings, userdata, gui
from slyguy.constants import ADDON_DEV, KODI_VERSION
from slyguy.util import get_kodi_string, set_kodi_string, kodi_rpc, kodi_db
from slyguy.log import log

from .constants import *

def _clean_tables(db_name, tables):
    if not tables or not db_name:
        return

    db_path = kodi_db(db_name)
    if not db_path:
        return

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        c = conn.cursor()

        for table in tables:
            c.execute("DELETE FROM {};".format(table))

        c.execute("VACUUM;")
        conn.commit()
    except:
        raise
    else:
        log.debug('DB Cleaned: {}'.format(db_path))
    finally:
        conn.close()

def start():
    monitor = xbmc.Monitor()
    restart_queued = False

    boot_merge = settings.getBool('boot_merge', False)
    set_kodi_string('_iptv_merge_force_run')

    while not monitor.waitForAbort(1):
        forced = ADDON_DEV or get_kodi_string('_iptv_merge_force_run') or 0

        if forced or boot_merge or (settings.getBool('auto_merge', True) and time.time() - userdata.get('last_run', 0) > settings.getInt('reload_time_hours', 12) * 3600):
            set_kodi_string('_iptv_merge_force_run', '1')

            url = router.url_for('service_merge', forced=forced)
            dirs, files = xbmcvfs.listdir(url)
            msg = unquote(files[0])

            if msg == 'ok':
                restart_queued = True

            userdata.set('last_run', int(time.time()))
            set_kodi_string('_iptv_merge_force_run')

        if restart_queued and settings.getBool('restart_pvr', False):
            if forced: progress = gui.progressbg(heading='Reloading IPTV Simple Client')

            if forced or (not xbmc.getCondVisibility('Pvr.IsPlayingTv') and not xbmc.getCondVisibility('Pvr.IsPlayingRadio')):
                restart_queued = False

                kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': False})

                wait_delay = 4
                for i in range(wait_delay):
                    if monitor.waitForAbort(1):
                        break
                    if forced: progress.update((i+1)*int(100/wait_delay))

                if settings.getBool('clean_dbs', True):
                    try: _clean_tables('tv', ['channelgroups', 'channels', 'map_channelgroups_channels'])
                    except: pass
                    try: _clean_tables('epg', ['epg', 'epgtags', 'lastepgscan'])
                    except: pass

                kodi_rpc('Addons.SetAddonEnabled', {'addonid': IPTV_SIMPLE_ID, 'enabled': True})

            if forced:
                progress.update(100)
                progress.close()

        boot_merge = False
        if ADDON_DEV:
            break