import arrow
from kodi_six import xbmc

from slyguy import gui, plugin
from slyguy.log import log

from .constants import POLL_TIME
from .language import _
from .settings import settings


@plugin.route('')
def index(**kwargs):
    plugin.redirect(plugin.url_for(plugin.ROUTE_SETTINGS))


def callback():
    function = settings.get('function')

    if not settings.getBool('silent', False):
        gui.notification(_(_.RUN_FUNCTION, function=function))

    log.debug('Running function: {}'.format(function))
    xbmc.executebuiltin(function)


def service():
    monitor = xbmc.Monitor()

    prev_kodi_time = None

    while not monitor.waitForAbort(POLL_TIME):
        kodi_time = arrow.now().timestamp

        if not prev_kodi_time:
            prev_kodi_time = kodi_time
            continue

        diff = kodi_time - prev_kodi_time
        if diff > (POLL_TIME + 30) or diff < 0:
            callback()

        prev_kodi_time = kodi_time
