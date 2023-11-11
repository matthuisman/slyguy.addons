import sys

from kodi_six import xbmcaddon
from six.moves.urllib.parse import unquote_plus

from lib import gui


CWD = xbmcaddon.Addon().getAddonInfo('path')


try:
    params = dict(arg.split('=') for arg in sys.argv[1].split('&'))
except:
    params = {}

searchstring = unquote_plus(params.get('searchstring',''))
if searchstring:
    del params['searchstring']
else:
    searchstring = gui.search()
    if not searchstring:
        sys.exit(0)

ui = gui.GUI('script-globalsearch.xml', CWD, 'default', '1080i', True, searchstring=searchstring, params=params)
ui.doModal()
del ui
