import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.realpath(os.path.join(path, 'resources/modules')))

try:
    from resources.lib import service
    service.start()
except Exception as e:
    import traceback
    import xbmc, xbmcgui
    xbmc.log('Failed to import Slyguy common service', xbmc.LOGFATAL)
    traceback.print_exc()
    xbmc.log('Updating add-ons', xbmc.LOGDEBUG)
    xbmc.executebuiltin('UpdateAddonRepos')
    xbmcgui.Dialog().ok('SlyGuy Error', 'Error starting Slyguy common service.\nPlease restart kodi and try again.')
