import os
import shutil
import re
from xml.dom.minidom import parseString

from . import util
from . import config

def retropie(partitions):
    try:
        dst = util.partition_mount(partitions[1], 'rw')

        path = os.path.join(dst, 'home', 'pi', 'RetroPie', 'roms', 'kodi')
        util.cmd("mkdir -p '{0}'".format(path))

        content = """#!/bin/sh
sudo su -c '(echo {0} > /sys/module/bcm270?/parameters/reboot_part && reboot) || reboot {0}'""".format(util.my_partition_number())

        util.write_file(os.path.join(path, 'kodi.sh'), content)
        util.cmd("chmod +x '{0}' && chown -R 1000:1000 '{1}'".format(os.path.join(path, 'kodi.sh'), path))

        with open(os.path.join(dst, 'etc', 'emulationstation', 'es_systems.cfg')) as f:
            doc = parseString(f.read())

        system = parseString("""<system>
    <fullname>Kodi</fullname>
    <name>kodi</name>
    <path>/home/pi/RetroPie/roms/kodi</path>
    <extension>.sh .SH</extension>
    <command>bash %ROM%</command>
    <platform>kodi</platform>
    <theme>kodi</theme>
</system>""").documentElement

        doc.childNodes[0].appendChild(system)

        config_path = os.path.join(dst, 'opt', 'retropie', 'configs', 'all', 'emulationstation', 'es_systems.cfg')
        util.write_file(config_path, doc.toxml())
    except:
        raise
    finally:
        util.partition_umount(partitions[1])

def raspbian(partitions):
    try:
        dst = util.partition_mount(partitions[1], 'rw')

        path = os.path.join(dst, 'home', 'pi', '.' + config.__addonid__)
        util.cmd("mkdir -p '{0}'".format(path))

        content = """#!/bin/sh
sudo su -c '(echo {0} > /sys/module/bcm270?/parameters/reboot_part && reboot) || reboot {0}'""".format(util.my_partition_number())

        util.write_file(os.path.join(path, 'launcher.sh'), content)

        cmd = "chmod +x '{0}'".format(os.path.join(path, 'launcher.sh'))
        cmd += " && cp -rf '{0}' '{1}'".format(os.path.join(config.__files_path__, 'kodi.png'), os.path.join(path, 'icon.png'))
        cmd += " && chown -R 1000:1000 '{0}'".format(path)

        path = os.path.join(dst, 'home', 'pi', 'Desktop')
        cmd += " && mkdir -p '{0}'".format(path)

        util.cmd(cmd)

        content = """[Desktop Entry]
Name=KODI
Comment=KODI
Icon=/home/pi/{0}/icon.png
Exec=/bin/sh /home/pi/{0}/launcher.sh
Type=Application
Encoding=UTF-8
Terminal=false
Categories=None;""".format('.' + config.__addonid__)

        desktop_file = os.path.join(path, config.__addonid__ + '.desktop')
        util.write_file(desktop_file, content)
        util.cmd("chown -R 1000:1000 '{0}'".format(path))
    except:
        raise
    finally:
        util.partition_umount(partitions[1])

def batocera(partitions):
    ## Install boot-back ##
    try:
        dst = util.partition_mount(partitions[1], 'rw')

        content = """#!/bin/sh
mount -o remount,rw /
cat <<EOT > /usr/bin/batocera-kodilauncher
#!/bin/bash
(echo {0} > /sys/module/bcm270?/parameters/reboot_part && reboot) || reboot {0} || /media/SHARE/system/part_reboot {0}
sleep 5
EOT
mount -o remount,ro /""".format(util.my_partition_number())

        file_path = os.path.join(dst, 'system', 'custom.sh')
        util.cmd("mkdir -p '{0}'".format(os.path.dirname(file_path)))
        util.write_file(file_path, content)

        cmd = "chmod +x '{0}'".format(file_path)
        cmd += " && cp -rf '{0}' '{1}' && chmod +x '{1}'".format(config.DATA['system']['part_reboot'], os.path.join(dst, 'system', 'part_reboot'))
        cmd += " && (sed '{0}' -i -e 's|kodi.atstartup.*|kodi.atstartup=0|' || true)".format(os.path.join(dst, 'system', 'batocera.conf'))
        util.cmd(cmd)
    except: raise
    finally: util.partition_umount(partitions[1])

    ## Fix cmdline.txt ##
    try:
        dst = util.partition_mount(partitions[0], 'rw')
        file_path = os.path.join(dst, 'cmdline.txt')
        util.cmd("sed '{0}' -i -e 's|dev=[^ ]*|dev={1}|'".format(file_path, partitions[0]))
    except: pass
    finally: util.partition_umount(partitions[0])

def recalbox(partitions):
    ## Install boot-back ##
    try:
        dst = util.partition_mount(partitions[2], 'rw')

        content = """#!/bin/bash
(echo {0} > /sys/module/bcm270?/parameters/reboot_part && reboot) || reboot {0} || /recalbox/scripts/part_reboot {0}
sleep 5""".format(util.my_partition_number())

        file_path = os.path.join(dst, 'upper', 'recalbox', 'scripts', 'kodilauncher.sh')
        util.cmd("mkdir -p '{0}'".format(os.path.dirname(file_path)))
        util.write_file(file_path, content)

        cmd = "chmod +x '{0}'".format(file_path)
        cmd += " && cp -rf '{0}' '{1}' && chmod +x '{1}'".format(config.DATA['system']['part_reboot'], os.path.join(dst, 'upper', 'recalbox', 'scripts', 'part_reboot'))
        util.cmd(cmd)
    except:
        raise
    finally:
        util.partition_umount(partitions[2])

    ## Remove kodi at startup config ##
    try:
        dst = util.partition_mount(partitions[1], 'rw')
        util.cmd("(sed '{0}' -i -e 's|kodi.atstartup.*|kodi.atstartup=0|' || true)".format(os.path.join(dst, 'system', 'recalbox.conf')))
    except: pass
    finally: util.partition_umount(partitions[1])

def lakka(partitions):
    try:
        dst = util.partition_mount(partitions[1], 'rw')

        content = """[Service]
Restart=on-failure
ExecStopPost=/bin/bash -c '[ $SERVICE_RESULT = "success" ] && reboot {0}'
""".format(util.my_partition_number())

        file_path = os.path.join(dst, '.config', 'system.d', 'retroarch.service.d', '10-kodi-boot-back.conf')
        util.cmd("mkdir -p '{0}'".format(os.path.dirname(file_path)))
        util.write_file(file_path, content)
    except:
        raise
    finally:
        util.partition_umount(partitions[1])
