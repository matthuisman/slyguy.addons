import os
import re
import json
import codecs

from kodi_six import xbmc, xbmcaddon

__addon__           = xbmcaddon.Addon()
__addonid__         = __addon__.getAddonInfo('id')
__addonversion__    = __addon__.getAddonInfo('version')
__addonname__       = __addon__.getAddonInfo('name')
__language__        = __addon__.getLocalizedString
__addonpath__       = xbmc.translatePath(__addon__.getAddonInfo('path'))
__datapath__        = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__files_path__      = os.path.join(__addonpath__, 'resources', 'files')
__data_file__       = os.path.join(__datapath__, 'data.json')
__partition_pattern = re.compile(r'^(/dev/.*[^0-9])([0-9]+)$')
__recovery_part__   = 1
__settings_part__   = 5

LIBREELEC = 'LibreELEC'
OSMC = 'OSMC'
XBIAN = 'XBIAN'
NOT_SUPPORTED = 'Not Supported'

if os.path.exists('/storage/.kodi'):
    __system__ = LIBREELEC
    __boot__   = '/flash'
    __reboot__ = "reboot {0}"
    __cmd__    = '{0}'
elif os.path.exists('/home/osmc'):
    __system__ = OSMC
    __boot__   = '/boot'
    __reboot__ = "reboot {0}"
    __cmd__    = 'sudo su -c "{0}"'
elif os.path.exists('/home/xbian'):
    __system__ = XBIAN
    __boot__   = "/boot"
    __reboot__ = "'{1}' {0}"
    __cmd__    = 'echo raspberry | sudo -S su -c "{0}"'
else:
    __system__ = NOT_SUPPORTED

if not os.path.exists(__datapath__):
    os.mkdir(__datapath__)

try:
    with codecs.open(__data_file__, 'r', encoding='utf8') as f:
        DATA = json.load(f)
except:
    DATA = {'user':{}, 'system':{}}

def save_data():
    with codecs.open(__data_file__, 'w', encoding='utf8') as f:
        f.write(json.dumps(DATA, ensure_ascii=False))

__systems__ = [
    # https://downloads.raspberrypi.org/os_list_v3.json #
    {'pattern': 'LibreELEC', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/libreelec.png'},
    {'pattern': 'OSMC', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/osmc.png'},
    {'pattern': 'Lakka', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/lakka.png', 'boot-back': 'lakka'},
    {'pattern': 'RaspbianLite', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/raspbian.png'},
    {'pattern': 'Raspbian', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/raspbian.png', 'boot-back': 'raspbian'},
    {'pattern': 'Screenly', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/screenlyose.png'},
    {'pattern': 'RISC', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/riscos.png'},
    {'pattern': 'Windows', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/windows10iotcore.png'},
    {'pattern': 'TLXOS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/tlxos.png'},

    # https://raw.githubusercontent.com/procount/pinn-os/master/os/os_list_v3.json #
    {'pattern': 'AIYprojects', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/aiyprojects.png'},
    {'pattern': 'CStemBian', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/cstembian.png'},
    {'pattern': 'PiTop', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/pitop.png'},
    {'pattern': 'solydx', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/solydx.png'},
    {'pattern': 'ubuntuMate1604LTS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/ubuntu-mate.png'},
    {'pattern': 'openelec', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/openelec.png'},
    {'pattern': 'XBian', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/xbian.png'},
    {'pattern': 'Retropie', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/retropie.png', 'boot-back': 'retropie'},
    {'pattern': 'kali', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/kali.png'},
    {'pattern': 'rtandroid', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/rtandroid.png'},
    {'pattern': 'lede2', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/lede2.png'},
    {'pattern': 'Arch', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/arch.png'},
    {'pattern': 'void', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/void.png'},
    {'pattern': 'gentoo', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/gentoo.png'},
    {'pattern': 'hypriotos', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/hypriot.png'},
    {'pattern': 'raspberry-vi', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/raspberry-vi.png'},
    {'pattern': 'picoreplayer', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/picoreplayer.png'},
    {'pattern': 'quirky', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/quirky.png'},
    {'pattern': 'lineage', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/lineage.png'},

    # https://raw.githubusercontent.com/matthuisman/pinn-os/master/os/os_list_v3.json #
    {'pattern': 'batocera', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/batocera.png', 'boot-back': 'batocera'},
    {'pattern': 'Kano_OS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/kano_os.png'},
    {'pattern': 'RasPlex', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/rasplex.png'},
    {'pattern': 'PiMusicBox', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/pimusicbox.png'},
    {'pattern': 'RetroX', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/retrox.png'},
    {'pattern': 'FlintOS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/flintos.png'},
    {'pattern': 'FedBerry', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/fedberry.png'},
    {'pattern': 'Amibian', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/amibian.png'},
    {'pattern': 'Gladys', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/gladys.png'},
    {'pattern': 'DietPi', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/dietpi.png'},
    {'pattern': 'resinOS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/resinos.png'},
    {'pattern': 'recalbox', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/recalboxos.png', 'boot-back': 'recalbox'},

    # Built-in
    {'pattern': 'NOOBS', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/noobs.png'},
    {'pattern': 'PINN', 'icon': 'https://k.slyguy.xyz/.images/noobs-companion/pinn.png'},
]