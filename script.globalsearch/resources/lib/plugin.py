from slyguy import plugin
from slyguy.constants import ROUTE_SCRIPT, ADDON_PATH, ADDON_ID, KODI_VERSION
from kodi_six import xbmc

from . import gui
from .language import _
from .settings import settings


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_.SEARCH, path=plugin.url_for(search))
    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder


@plugin.route()
def search(**kwargs):
    xbmc.executebuiltin('RunScript({})'.format(ADDON_ID))


@plugin.route(ROUTE_SCRIPT)
def script(searchstring=None, **kwargs):
    if KODI_VERSION < 18:
        plugin.exception("Kodi 18+ is required to use this addon")

    searchstring = searchstring or gui.search()
    if not searchstring:
        return

    ui = gui.GUI('script-globalsearch.xml', ADDON_PATH, 'default', '1080i', True, searchstring=searchstring, params={})
    ui.doModal()
    del ui
