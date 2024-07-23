import os
import sys
import shutil
import time

from kodi_six import xbmc, xbmcaddon, xbmcplugin

from slyguy import gui, router, _
from slyguy.constants import ADDON_ID, ADDON_PROFILE, ROUTE_MIGRATE_DONE


def get_addon(addon_id):
    try:
        return xbmcaddon.Addon(addon_id)
    except:
        return None

def _handle():
    try: return int(sys.argv[1])
    except: return -1

# Runs on old add-on
def migrate(new_addon_id, copy_userdata=True, message=_.CONFIRM_MIGRATE):
    do_migrate(new_addon_id, copy_userdata, message)

    handle = _handle()
    if handle > 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)

# Runs on old add-on
def do_migrate(new_addon_id, copy_userdata, message):
    migrate_done_url = router.url_for(ROUTE_MIGRATE_DONE, old_addon_id=ADDON_ID, _addon_id=new_addon_id)

    if get_addon(new_addon_id):
        xbmc.executebuiltin('RunPlugin({})'.format(migrate_done_url))
        return

    if not gui.yes_no(_(message, new_addon_id=new_addon_id, old_addon_id=ADDON_ID)):
        return

    xbmc.executebuiltin('InstallAddon({})'.format(new_addon_id), True)
    time.sleep(0.5)
    xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":true}}}}'.format(new_addon_id))

    dst_addon = get_addon(new_addon_id)
    if not dst_addon:
        return gui.ok(_.MIGRATE_ADDON_NOT_FOUND)

    if copy_userdata and os.path.exists(ADDON_PROFILE):
        dst_profile = xbmc.translatePath(dst_addon.getAddonInfo('profile'))

        if os.path.exists(dst_profile):
            shutil.rmtree(dst_profile)

        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":false}}}}'.format(ADDON_ID))
        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":false}}}}'.format(new_addon_id))

        shutil.copytree(ADDON_PROFILE, dst_profile)

        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":true}}}}'.format(new_addon_id))

    handle = _handle()
    if handle > 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)
        
    xbmc.executebuiltin('RunPlugin({})'.format(migrate_done_url))

# Runs on new add-on
@router.route(ROUTE_MIGRATE_DONE)
def migrate_done(old_addon_id):
    if gui.yes_no(_(_.MIGRATE_OK, old_addon_id=old_addon_id)):
        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":true}}}}'.format(old_addon_id))

        old_addon = get_addon(old_addon_id)
        if not old_addon:
            return

        xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{}","enabled":false}}}}'.format(old_addon_id))

        old_addon_dir =  xbmc.translatePath(old_addon.getAddonInfo('path'))
        old_profile = xbmc.translatePath(old_addon.getAddonInfo('profile'))

        if os.path.exists(old_addon_dir):
            shutil.rmtree(old_addon_dir)

        if os.path.exists(old_profile):
            shutil.rmtree(old_profile)

    gui.redirect(router.url_for(''))