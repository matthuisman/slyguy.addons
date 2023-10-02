import sys
import datetime

from .log import log
from .constants import ADDON_ID, COMMON_ADDON_ID, DEPENDENCIES_ADDON_ID

# python embedded (as used in kodi) has a known bug for second calls of strptime.
# The python bug is docmumented here https://bugs.python.org/issue27400
# The following workaround patch is borrowed from https://forum.kodi.tv/showthread.php?tid=112916&pid=2914578#pid2914578
class proxydt(datetime.datetime):
    @staticmethod
    def strptime(date_string, format):
        import time
        return datetime.datetime(*(time.strptime(date_string, format)[0:6]))

log.debug('patching datetime.datetime')
datetime.datetime = proxydt

log.debug('sys.path: {}'.format(sys.path))
if ADDON_ID not in sys.path[0]:
    paths = [None, None, None]
    for path in sys.path:
        if COMMON_ADDON_ID in path and 'modules' in path:
            paths[1] = path
        elif DEPENDENCIES_ADDON_ID in path and 'modules' in path:
            paths[2] = path
        elif ADDON_ID in path:
            paths[0] = path
    sys.path = [x for x in paths if x] + [x for x in sys.path if x not in paths]
    log.debug('Fixed sys.path: {}'.format(sys.path))
