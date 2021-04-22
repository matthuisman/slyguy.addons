import os
import sys
import re
import shutil
import json
import time
import subprocess
import traceback

from kodi_six import xbmc
from six.moves.configparser import ConfigParser
from six import StringIO

from . import config

def cmd(cmd, wait=True):
    if 'su -c' in config.__cmd__:
        cmd = cmd.replace('$', '\$')
        
    cmd = config.__cmd__.format(cmd)
    print(cmd)
    
    if not wait:
        try:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        except:
            traceback.print_exc()
            raise Exception('Cmd failed: {0}'.format(cmd))
    else:
        try:
            return subprocess.check_output(cmd, shell=True).strip()
        except:
            traceback.print_exc()
            raise Exception('Cmd failed: {0}'.format(cmd))

def my_partition_number():
    return partition_number(config.DATA['system']['my_partition'])

def write_file(file_path, content):
    temp_file = os.path.join(config.__datapath__, os.path.basename(file_path))
    with open(temp_file, 'w') as f:
        f.write(content)

    cmd("cp -rf '{0}' '{1}'".format(temp_file, file_path))
    cmd("rm -f '{0}'".format(temp_file))
    if not os.path.exists(file_path):
        raise Exception("Failed to copy file to %s" % file_path)

def partition_mount(partition, mode='ro'):
    mount_info = get_mounts().get(partition)
    if mount_info:
        if mode == 'ro' or mode == mount_info['mode']:
            return mount_info['mount']
        else:
            partition_umount(partition)

    dst = os.path.join(config.__datapath__, os.path.basename(partition))
    try:
        cmd("mkdir -p '{2}' && mount -t auto -o {0} {1} '{2}'".format(mode, partition, dst))
    except:
        raise Exception("Failed to mount: {0}".format(partition))

    return dst

def partition_umount(partition):
    dst = os.path.join(config.__datapath__, os.path.basename(partition))
    cmd("( umount '{0}' || true ) && ( rmdir '{0}' || true )".format(dst))

def get_boot_cmd(partition):
    part = partition_number(partition)
    return config.__reboot__.format(part, config.DATA['system']['part_reboot'])

def partition_boot(partition):
    cmd(get_boot_cmd(partition), wait=False)

def partition_number(partition):
    return int(config.__partition_pattern.match(partition).group(2))

def partition_defaultboot(partition):
    try:
        settings_path = partition_mount(config.DATA['system']['settings_partition'], 'rw')
        conf_path = os.path.join(settings_path, 'noobs.conf')

        noobs_conf = ConfigParser()
        noobs_conf.read(conf_path)

        section = 'General'

        if not noobs_conf.has_section(section):
            noobs_conf.add_section(section)

        if partition == config.DATA['system']['recovery_partition']:
            noobs_conf.remove_option(section, 'default_partition_to_boot')
            noobs_conf.remove_option(section, 'sticky_boot')
        else:
            noobs_conf.set(section, 'default_partition_to_boot', str(partition_number(partition)))
            noobs_conf.set(section, 'sticky_boot', str(partition_number(partition)))

        output = StringIO()
        noobs_conf.write(output)
        write_file(conf_path, output.getvalue())
    except:
        raise
    finally:
        partition_umount(config.DATA['system']['settings_partition'])

def get_systems():
    systems = config.DATA['system'].get('systems', {})
    for key in systems:
        systems[key].update(config.DATA['user'].get(key, {}))
    return systems

def get_system(system_key):
    systems = get_systems()
    for key in systems:
        if key == system_key:
            return systems[key]
    return None

def update_system(system_key, data):
    config.DATA['user'].setdefault(system_key, data)
    config.DATA['user'][system_key].update(data)
    config.save_data()

def delete_data():
    os.remove(config.__data_file__)

def get_system_info(system_key):
    for info in config.__systems__:
        if re.search(info['pattern'], system_key, re.IGNORECASE):
            return info
    return {}

def get_system_key(name):
    return name.replace(' ','').lower().strip()

def get_mounts():
    mounts = {}
    with open('/proc/mounts','r') as f:
        for line in f.readlines():
            mount = line.split()
            if config.__partition_pattern.match(mount[0]) and '/dev/loop' not in mount[0]:
                mounts[mount[0]] = {'mount':mount[1], 'mode':mount[3].split(',')[0]}
    return mounts

def init():
    if config.DATA['system'].get('version', '') == config.__addonversion__:
        return

    config.DATA['system'] = {'version': config.__addonversion__}

    mounts = get_mounts()
    for mount in mounts:
        if mounts[mount]['mount'] == config.__boot__:
            config.DATA['system']['my_partition'] = mount

    boot_device = config.__partition_pattern.match(config.DATA['system']['my_partition']).group(1)
    config.DATA['system']['recovery_partition'] = boot_device + str(config.__recovery_part__)
    config.DATA['system']['settings_partition'] = boot_device + str(config.__settings_part__)
    config.DATA['system']['part_reboot'] = os.path.join(config.__files_path__, 'part_reboot')
    cmd("chmod +x '{0}'".format(config.DATA['system']['part_reboot']))

    _build_systems()
    config.save_data()

def _build_systems():
    config.DATA['system']['systems'] = {}

    try:
        recovery_path = partition_mount(config.DATA['system']['recovery_partition'])
        settings_path = partition_mount(config.DATA['system']['settings_partition'])
        
        with open(os.path.join(settings_path, 'installed_os.json')) as f:
            raw_systems = json.loads(f.read())

        sys_name = 'NOOBS'
        try:
            with open(os.path.join(recovery_path, 'recovery.cmdline')) as f:
                data = f.read()
                
            if 'alt_image_source' in data or 'repo_list' in data:
                sys_name = 'PINN'
        except:
            pass

        raw_systems.append({
            'description' : 'An easy Operating System install manager for the Raspberry Pi',
            'bootable' : True,
            'partitions' : [config.DATA['system']['recovery_partition']],
            'name' : sys_name,
            })

        for system in raw_systems:
            if not system['bootable'] or not system['partitions']: 
                continue

            system_key = get_system_key(system['name'])
            system_info = get_system_info(system_key)

            icon_path = system_info.get('icon', None)
            if not icon_path:
                noobs_path = system.get('icon','').replace('/mnt', recovery_path).replace('/settings', settings_path)
                if os.path.isfile(noobs_path):
                    try:
                        icon_path = os.path.join(config.__datapath__, system_key + '.png')
                        shutil.copy(noobs_path, icon_path)
                    except:
                        icon_path = None

            partitions = []
            for partition in system['partitions']:
                if partition.startswith('PARTUUID'):
                    path = '/dev/disk/by-partuuid/{}'.format(partition.split('=')[1])
                    partition = os.path.realpath(path)

                partitions.append(partition)

            system['partitions'] = partitions
            system['icon'] = icon_path
            config.DATA['system']['systems'][system_key] = system
    except:
        raise

    finally:
        partition_umount(config.DATA['system']['recovery_partition'])
        partition_umount(config.DATA['system']['settings_partition'])