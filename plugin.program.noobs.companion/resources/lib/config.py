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

IMAGE_URL = 'https://i.mjh.nz/.images/noobs-companion/'
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
    {'pattern': 'LibreELEC', 'icon': IMAGE_URL+'libreelec.png'},
    {'pattern': 'OSMC', 'icon': IMAGE_URL+'osmc.png'},
    {'pattern': 'Lakka', 'icon': IMAGE_URL+'lakka.png', 'boot-back': 'lakka'},
    {'pattern': 'RaspbianLite', 'icon': IMAGE_URL+'raspbian.png'},
    {'pattern': 'Raspbian', 'icon': IMAGE_URL+'raspbian.png', 'boot-back': 'raspbian'},
    {'pattern': 'Screenly', 'icon': IMAGE_URL+'screenlyose.png'},
    {'pattern': 'RISC', 'icon': IMAGE_URL+'riscos.png'},
    {'pattern': 'Windows', 'icon': IMAGE_URL+'windows10iotcore.png'},
    {'pattern': 'TLXOS', 'icon': IMAGE_URL+'tlxos.png'},

    # https://raw.githubusercontent.com/procount/pinn-os/master/os/os_list_v3.json #
    {'pattern': 'AIYprojects', 'icon': IMAGE_URL+'aiyprojects.png'},
    {'pattern': 'CStemBian', 'icon': IMAGE_URL+'cstembian.png'},
    {'pattern': 'PiTop', 'icon': IMAGE_URL+'pitop.png'},
    {'pattern': 'solydx', 'icon': IMAGE_URL+'solydx.png'},
    {'pattern': 'ubuntuMate1604LTS', 'icon': IMAGE_URL+'ubuntu-mate.png'},
    {'pattern': 'openelec', 'icon': IMAGE_URL+'openelec.png'},
    {'pattern': 'XBian', 'icon': IMAGE_URL+'xbian.png'},
    {'pattern': 'Retropie', 'icon': IMAGE_URL+'retropie.png', 'boot-back': 'retropie'},
    {'pattern': 'kali', 'icon': IMAGE_URL+'kali.png'},
    {'pattern': 'rtandroid', 'icon': IMAGE_URL+'rtandroid.png'},
    {'pattern': 'lede2', 'icon': IMAGE_URL+'lede2.png'},
    {'pattern': 'Arch', 'icon': IMAGE_URL+'arch.png'},
    {'pattern': 'void', 'icon': IMAGE_URL+'void.png'},
    {'pattern': 'gentoo', 'icon': IMAGE_URL+'gentoo.png'},
    {'pattern': 'hypriotos', 'icon': IMAGE_URL+'hypriot.png'},
    {'pattern': 'raspberry-vi', 'icon': IMAGE_URL+'raspberry-vi.png'},
    {'pattern': 'picoreplayer', 'icon': IMAGE_URL+'picoreplayer.png'},
    {'pattern': 'quirky', 'icon': IMAGE_URL+'quirky.png'},
    {'pattern': 'lineage', 'icon': IMAGE_URL+'lineage.png'},

    # https://raw.githubusercontent.com/matthuisman/pinn-os/master/os/os_list_v3.json #
    {'pattern': 'batocera', 'icon': IMAGE_URL+'batocera.png', 'boot-back': 'batocera'},
    {'pattern': 'Kano_OS', 'icon': IMAGE_URL+'kano_os.png'},
    {'pattern': 'RasPlex', 'icon': IMAGE_URL+'rasplex.png'},
    {'pattern': 'PiMusicBox', 'icon': IMAGE_URL+'pimusicbox.png'},
    {'pattern': 'RetroX', 'icon': IMAGE_URL+'retrox.png'},
    {'pattern': 'FlintOS', 'icon': IMAGE_URL+'flintos.png'},
    {'pattern': 'FedBerry', 'icon': IMAGE_URL+'fedberry.png'},
    {'pattern': 'Amibian', 'icon': IMAGE_URL+'amibian.png'},
    {'pattern': 'Gladys', 'icon': IMAGE_URL+'gladys.png'},
    {'pattern': 'DietPi', 'icon': IMAGE_URL+'dietpi.png'},
    {'pattern': 'resinOS', 'icon': IMAGE_URL+'resinos.png'},
    {'pattern': 'recalbox', 'icon': IMAGE_URL+'recalboxos.png', 'boot-back': 'recalbox'},

    # Built-in
    {'pattern': 'NOOBS', 'icon': IMAGE_URL+'noobs.png'},
    {'pattern': 'PINN', 'icon': IMAGE_URL+'pinn.png'},
]
