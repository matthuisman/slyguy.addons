import sys
import xbmc, xbmcaddon, xbmcplugin, xbmcgui

trailer_addon_id = 'slyguy.trailers'
addon_id = xbmcaddon.Addon().getAddonInfo('id')

url = sys.argv[0] + sys.argv[2]
new_url = url.replace(addon_id, trailer_addon_id)
xbmc.log("{} - Re-routing {} -> {}".format(addon_id, url, new_url))

li = xbmcgui.ListItem(path=new_url)
xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
