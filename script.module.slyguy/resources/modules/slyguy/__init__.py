import sys

from .log import log
from .constants import ADDON_ID, COMMON_ADDON_ID, DEPENDENCIES_ADDON_ID

if DEPENDENCIES_ADDON_ID in sys.path[-1]:
    if ADDON_ID == DEPENDENCIES_ADDON_ID:
        index = 1
    elif ADDON_ID == COMMON_ADDON_ID:
        index = 2
    else:
        index = 3
    new_path = sys.path[-index:] + sys.path[:-index]
    log.debug('Fix for wrong sys.path in Kodi 20+ (xbmc/issues/22985)\nOld: {}\nNew: {}'.format(sys.path, new_path))
    sys.path = new_path
