import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.realpath(os.path.join(path, 'resources/modules')))

try:
    from resources.lib import service
except Exception as e:
    import traceback
    import xbmc, xbmcgui
    xbmc.log('Failed to import Slyguy common service', xbmc.LOGFATAL)
    traceback.print_exc()
    if xbmcgui.Dialog().ok('SlyGuy Error', 'Error importing Slyguy common service\nThis major bug is usually fixed very quickly\n[B]Click OK to check for updates[/B]'):
        xbmc.executebuiltin('UpdateAddonRepos')
else:
    service.run()
