import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.realpath(os.path.join(path, 'resources/modules')))

try:
    from resources.lib import service
except Exception as e:
    import traceback
    import xbmc, xbmcgui

    if 'Unknown addon id' in str(e):
        xbmc.log('Slyguy common updating. Expected error: {}'.format(e), xbmc.LOGINFO)
        sys.exit(0)

    xbmc.log('Failed to import Slyguy common service: {}'.format(traceback.format_exc()), xbmc.LOGERROR)
    if xbmcgui.Dialog().ok('SlyGuy Error', 'Error starting Slyguy common service\nThis major bug is usually fixed very quickly\n[B]Click OK to check for updates[/B]'):
        xbmc.executebuiltin('UpdateAddonRepos')
else:
    service.run()
