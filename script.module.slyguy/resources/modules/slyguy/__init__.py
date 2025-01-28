import sys
import datetime

from slyguy.language import _
from slyguy.log import log
from slyguy.settings import settings, is_donor, check_donor, set_drm_level
from slyguy.constants import ADDON_ID, COMMON_ADDON_ID, DEPENDENCIES_ADDON_ID


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


#fix for datatetime.strptime returns None
class proxydt(datetime.datetime):
    @staticmethod
    def strptime(date_string, format):
        import time
        return datetime.datetime(*(time.strptime(date_string, format)[0:6]))

datetime.datetime = proxydt
