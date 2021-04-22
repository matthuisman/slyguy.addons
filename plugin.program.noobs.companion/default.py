import os
import sys
import time
import traceback

from six.moves.urllib_parse import parse_qsl
from kodi_six import xbmc, xbmcplugin, xbmcgui

from resources.lib import util
from resources.lib import config

dialog = xbmcgui.Dialog()

def error(message):
    dialog.ok('ERROR!', str(message))

def boot_system(system_key):
    system = util.get_system(system_key)
    if not system:
        dialog.notification(config.__addonname__, 'Could not find system: {0}'.format(system_key), os.path.join(config.__addonpath__, 'icon.png'), 3000)
        return

    name = system.get('name', '')
    icon = system.get('icon', xbmcgui.NOTIFICATION_INFO)

    dialog.notification(name, 'Booting....', icon, 2000)
    time.sleep(1)
    util.partition_boot(system.get('partitions')[0])

def install_system(system_key):
    from resources.lib import install

    system = util.get_system(system_key)
    if not system:
        return

    name = system.get('name', '')
    icon = system.get('icon', xbmcgui.NOTIFICATION_INFO)

    function = getattr(install, util.get_system_info(system_key).get('boot-back', ''), None)
    if not function:
        dialog.notification(name, 'Currently not Boot-Back installable.', icon, 5000)
        return

    function(system.get('partitions'))
    dialog.notification(name, 'Boot-Back Installed', icon, 2000)
    xbmc.executebuiltin('Container.Refresh')

def defaultboot_system(system_key):
    system = util.get_system(system_key)
    if not system:
        return

    name = system.get('name', '')
    icon = system.get('icon', xbmcgui.NOTIFICATION_INFO)

    util.partition_defaultboot(system.get('partitions')[0])
    dialog.notification(name, 'Set to Default Boot', icon, 2000)

def rename_system(system_key):
    system = util.get_system(system_key)
    if not system:
        return

    kb = xbmc.Keyboard()
    kb.setHeading('Rename system')
    kb.setDefault(system.get('name',''))
    kb.doModal()
    if not kb.isConfirmed():
        return

    new_name = kb.getText()
    name = system.get('name', '')
    icon = system.get('icon', xbmcgui.NOTIFICATION_INFO)

    util.update_system(system_key, {'name' : new_name})
    xbmc.executebuiltin('Container.Refresh')

def set_icon_system(system_key):
    system = util.get_system(system_key)
    if not system:
        return

    new_icon = dialog.browseSingle(2, 'Choose a new icon', 'files')
    if not new_icon:
        return

    name = system.get('name', '')
    icon = system.get('icon', xbmcgui.NOTIFICATION_INFO)

    util.update_system(system_key, {'icon' : new_icon})
    xbmc.executebuiltin('Container.Refresh')

def showbootcommands(system_key):
    system = util.get_system(system_key)
    if not system:
        return

    kodi_cmd = 'RunPlugin({}\n  ?action=boot&system={})'.format(sys.argv[0], system_key)
    sys_cmd  = util.get_boot_cmd(system.get('partitions')[0])

    dialog.textviewer('Boot Commands', 'Kodi:\n[B]{}[/B]\n\nShell:\n[B]{}[/B]'.format(kodi_cmd, sys_cmd))

def clear_data():
    if dialog.yesno('Clear Data?', 'This will delete the current saved data for this addon.\nYou will lose any custom names / icons you have set.', ):
        util.delete_data()
        dialog.notification(config.__addonname__, 'Data cleared', os.path.join(config.__addonpath__, 'icon.png'), 3000)

def list_systems():
    systems = util.get_systems()

    for system_key in sorted(systems, key=lambda k: systems[k]['name']):
        system = systems[system_key]

        listitem = xbmcgui.ListItem()
        listitem.setLabel(system['name'])
        listitem.setArt({'thumb': system['icon']})

        context_items = [
            ('Rename', "RunPlugin({0}?action=rename&system={1})".format(sys.argv[0], system_key)),
            ('Set Icon', "RunPlugin({0}?action=set_icon&system={1})".format(sys.argv[0], system_key)),
            ('Set to Default Boot', "RunPlugin({0}?action=defaultboot&system={1})".format(sys.argv[0], system_key)),
            ('Show Boot Commands', "RunPlugin({0}?action=showbootcommands&system={1})".format(sys.argv[0], system_key)),
        ]

        if util.get_system_info(system_key).get('boot-back', None):
            context_items.extend((
                ('Install Boot-Back', "RunPlugin({0}?action=install&system={1})".format(sys.argv[0], system_key)),
            ))

        listitem.addContextMenuItems(context_items)

        action = "{0}?action=boot&system={1}".format(sys.argv[0], system_key)
        xbmcplugin.addDirectoryItem(int(sys.argv[1]), action, listitem, isFolder=False)

    xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

try:
    ## Doesnt work on Pi4: https://forum.kodi.tv/showthread.php?tid=346077&pid=2875293
    # if not xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
    #     dialog.ok("Not Supported", 'This addon only works on the Raspberry Pi range of boards.')
    #     sys.exit(0)

    if config.__system__ == config.NOT_SUPPORTED:
        dialog.ok("Not Supported", 'The supported systems are:\nLibreELEC, OpenELEC, OSMC & Xbian')
        sys.exit(0)

    try:
        util.init()
    except:
        dialog.ok("ERROR", 'Failed to initialise systems.\nPlease make sure you are using NOOBS or PINN.')
        sys.exit(0)

    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if action == 'boot':
        boot_system(params.get('system'))
    elif action == 'install':
        install_system(params.get('system'))
    elif action == 'defaultboot':
        defaultboot_system(params.get('system'))
    elif action == 'showbootcommands':
        showbootcommands(params.get('system'))
    elif action == 'rename':
        rename_system(params.get('system'))
    elif action == 'set_icon':
        set_icon_system(params.get('system'))
    elif action == 'clear':
        clear_data()
    else:
        list_systems()
except Exception as e:
    traceback.print_exc()
    error(e)