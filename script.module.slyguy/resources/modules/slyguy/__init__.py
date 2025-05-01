import sys
import xbmc, xbmcaddon

DEPENDENCIES_ADDON_ID = 'slyguy.dependencies'
COMMON_ADDON_ID = 'script.module.slyguy'
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
monitor = xbmc.Monitor()

# fix for asyncio crashes
sys.modules['_asyncio'] = None

xbmc.log('slyguy.common - sys.path: {}'.format(sys.path))
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
    xbmc.log('slyguy.common - Fixed sys.path: {}'.format(sys.path))


# have to come after sys path fixed so requests, urllib etc imported from our dependencies
from slyguy.log import log
from slyguy.language import _
from slyguy.settings import settings, is_donor, check_donor, set_drm_level
