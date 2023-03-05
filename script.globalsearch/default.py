import sys

from kodi_six import xbmc, xbmcaddon
from six.moves.urllib.parse import unquote_plus

from resources.lib import gui


LANGUAGE = xbmcaddon.Addon().getLocalizedString
CWD = xbmcaddon.Addon().getAddonInfo('path')

if (__name__ == '__main__'):
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

    ui = gui.GUI('script-globalsearch.xml', CWD, defaultSkin='default', defaultRes='1080i', isMedia=True, searchstring=searchstring, params=params)
    ui.doModal()
    del ui
