import time
import random

from kodi_six import xbmc

from . import settings
from .router import url_for
from .constants import ROUTE_SERVICE, ROUTE_SERVICE_INTERVAL

def run(interval=ROUTE_SERVICE_INTERVAL):
    url = url_for(ROUTE_SERVICE)
    cmd = 'RunPlugin({0})'.format(url)
    last_run = 0

    monitor = xbmc.Monitor()

    delay = settings.getInt('service_delay', 0) or random.randint(10, 60)
    monitor.waitForAbort(delay)

    while not monitor.abortRequested():
        if time.time() - last_run >= interval:
            xbmc.executebuiltin(cmd)
            last_run = time.time()
            
        monitor.waitForAbort(random.randint(5, 20))