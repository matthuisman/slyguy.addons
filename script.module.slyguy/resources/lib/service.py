import sys
import json
import uuid
from time import time

from slyguy import settings, signals, gui
from slyguy.session import Session
from slyguy.log import log
from slyguy.monitor import monitor
from slyguy.drm import set_drm_level
from slyguy.donor import is_donor
from slyguy.util import get_system_arch

from .proxy import Proxy
from .player import Player
from .util import check_updates, check_repo
from .constants import *
from .language import _

def _check_news():
    _time = int(time())
    if _time < settings.getInt('_last_news_check', 0) + NEWS_CHECK_TIME:
        return

    settings.setInt('_last_news_check', _time)

    with Session(timeout=15) as session:
        news = session.gz_json(NEWS_URL)
    if not news:
        return

    if 'id' not in news or news['id'] == settings.get('_last_news_id'):
        return

    settings.set('_last_news_id', news['id'])

    if news['type'] == 'donate' and is_donor():
        return

    settings.set('_news', json.dumps(news))

def _check_arch():
    arch = get_system_arch()[1]
    mac = str(uuid.getnode())

    prev_mac = settings.get('_mac')
    prev_arch = settings.get('_arch')
    settings.set('_arch', arch)
    settings.set('_mac', mac)
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

    proxy = Proxy()
    player = Player()

    try:
        proxy.start()
    except Exception as e:
        log.error('Failed to start proxy server')
        log.exception(e)

    is_donor(force=True)

    try:
        set_drm_level()
    except Exception as e:
        log.error('Failed to set DRM level')
        log.exception(e)

    try:
        _check_arch()
    except Exception as e:
        log.error('Failed to check arch')
        log.exception(e)

    ## Inital wait on boot
    monitor.waitForAbort(10)

    try:
        while not monitor.abortRequested():
            try:
                if is_donor() and settings.getBool('fast_updates'):
                    check_updates()

                if not is_donor() or settings.getBool('show_news'):
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

    log.debug('Shared Service: Stopped')
