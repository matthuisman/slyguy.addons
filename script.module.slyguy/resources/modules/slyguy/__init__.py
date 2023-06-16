import sys

import xbmc, xbmcaddon

xbmc.log('old sys.path: {}'.format(sys.path), xbmc.LOGDEBUG)
addon_id = xbmcaddon.Addon().getAddonInfo('id')
paths = [None, None, None]
for path in sys.path:
    if 'script.module.slyguy' in path and 'modules' in path:
        paths[1] = path
    elif 'slyguy.dependencies' in path and 'modules' in path:
        paths[2] = path
    elif addon_id in path:
        paths[0] = path
sys.path = [x for x in paths if x] + [x for x in sys.path if x not in paths]
xbmc.log('new sys.path: {}'.format(sys.path), xbmc.LOGDEBUG)
