import sys
import uuid
from time import time

from slyguy import signals, gui, settings, log, check_donor, is_donor, set_drm_level
from slyguy.session import Session
from slyguy.monitor import monitor
from slyguy.util import get_system_arch

from .proxy import Proxy
from .player import Player
from .util import check_updates, check_repo
from .constants import *
from .language import _


def _check_news():
    _time = int(time())
    if _time < settings.common_settings.getInt('_last_news_check', 0) + NEWS_CHECK_TIME:
        return

    settings.common_settings.setInt('_last_news_check', _time)

    with Session(timeout=15) as session:
        news = session.gz_json(NEWS_URL)
    if not news:
        return

    if 'id' not in news or news['id'] == settings.common_settings.get('_last_news_id'):
        return
    settings.common_settings.set('_last_news_id', news['id'])

    if news['type'] == 'donate' and is_donor():
        return
    settings.common_settings.setDict('_news', news)


def check_arch():
    arch = get_system_arch()[1]
    mac = int(uuid.getnode())

    prev_mac = settings.common_settings.getInt('_mac')
    prev_arch = settings.common_settings.get('_arch')
    settings.common_settings.set('_arch', arch)
    settings.common_settings.setInt('_mac', mac)
    if not prev_mac or not prev_arch:
        return

    if prev_mac == mac and prev_arch != arch:
        gui.ok(_(_.ARCH_CHANGED, old=prev_arch, new=arch))


@signals.on(signals.ON_SETTINGS_CHANGE)
def settings_changed():
    log.debug('Shared Service: Settings Changed')


def start():
    log.debug('Shared Service: Started')
    log.info('Python Version: {}'.format(sys.version))

    player = Player()
    proxy = Proxy()
    proxy.start()

    check_donor()
    set_drm_level()
    check_arch()

    ## Inital wait on boot
    monitor.waitForAbort(10)
    try:
        while not monitor.abortRequested():
            try:
                settings.common_settings.reset()
                check_donor()

                if is_donor() and settings.common_settings.getBool('fast_updates'):
                    check_updates()

                if not is_donor() or settings.common_settings.getBool('show_news'):
                    _check_news()

                check_repo()
            except Exception as e:
                log.debug('Service loop failed: {}'.format(e))

            if monitor.waitForAbort(30):
                break
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.exception(e)

    try: proxy.stop()
    except: pass

    try: del player
    except: pass

    log.debug('Shared Service: Stopped')
