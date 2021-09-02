import os
import platform
import re
import shutil
import time
import struct
import subprocess
from distutils.version import LooseVersion

from kodi_six import xbmc, xbmcaddon

from . import gui, settings
from .userdata import Userdata
from .session import Session
from .log import log
from .constants import *
from .language import _
from .util import md5sum, remove_file, get_system_arch, hash_6, kodi_rpc, get_addon
from .exceptions import InputStreamError

def get_id():
    return IA_ADDON_ID

def get_ia_addon(required=False, install=True):
    addon_id = get_id()

    addon = get_addon(addon_id, required=False, install=install)

    if not addon and addon_id == IA_ADDON_ID and install and get_system_arch()[0] == 'Linux':
        with gui.progress(_.INSTALLING_APT_IA, heading=_.IA_WIDEVINE_DRM, percent=20) as progress:
            try:
                subprocess.check_output('apt-get -y install {0} || sudo apt-get -y install {0}'.format(IA_LINUX_PACKAGE), shell=True)
                log.debug('{} installed'.format(IA_LINUX_PACKAGE))
                progress.update(70)
                xbmc.executebuiltin('UpdateLocalAddons()')

                max_wait = 5
                for i in range(max_wait):
                    xbmc.sleep(1000)
                    progress.update(70+(i*(30/max_wait)))
                    addon = get_addon(addon_id, required=False, install=False)
                    if addon:
                        break
            except Exception as e:
                log.exception(e)
                log.debug('{} failed to install'.format(IA_LINUX_PACKAGE))

    if not addon and required:
        raise InputStreamError(_(_.ADDON_REQUIRED, addon_id=addon_id))

    return addon

class InputstreamItem(object):
    manifest_type = ''
    license_type  = ''
    license_key   = ''
    mimetype      = ''
    checked       = None
    license_data  = None
    challenge     = None
    response      = None
    properties    = None
    minversion    = None

    def __init__(self, minversion=None, properties=None):
        if minversion:
            self.minversion = minversion
        self.properties = properties or {}

    @property
    def addon_id(self):
        return get_id()

    def do_check(self):
        return False

    def check(self):
        if self.checked is None:
            self.checked = self.do_check()

        return self.checked

class HLS(InputstreamItem):
    manifest_type = 'hls'
    mimetype      = 'application/vnd.apple.mpegurl'
    minversion    = IA_HLS_MIN_VER

    def __init__(self, force=False, live=True, **kwargs):
        super(HLS, self).__init__(**kwargs)
        self.force = force
        self.live  = live

    def do_check(self):
        legacy   = settings.getBool('use_ia_hls', False)
        hls_live = settings.getBool('use_ia_hls_live', legacy)
        hls_vod  = settings.getBool('use_ia_hls_vod', legacy)
        return (self.force or (self.live and hls_live) or (not self.live and hls_vod)) and require_version(self.minversion, required=self.force)

class MPD(InputstreamItem):
    manifest_type = 'mpd'
    mimetype      = 'application/dash+xml'
    minversion    = IA_MPD_MIN_VER

    def do_check(self):
        return require_version(self.minversion, required=True)

class Playready(InputstreamItem):
    manifest_type = 'ism'
    license_type  = 'com.microsoft.playready'
    mimetype      = 'application/vnd.ms-sstr+xml'
    minversion    = IA_PR_MIN_VER

    def do_check(self):
        return require_version(self.minversion, required=True) and KODI_VERSION > 17 and xbmc.getCondVisibility('system.platform.android')

class Widevine(InputstreamItem):
    license_type = 'com.widevine.alpha'

    def __init__(self, license_key=None, content_type='application/octet-stream', challenge='R{SSM}', response='', manifest_type='mpd', mimetype='application/dash+xml', license_data=None, wv_secure=False, **kwargs):
        super(Widevine, self).__init__(**kwargs)
        self.license_key = license_key
        self.content_type = content_type
        self.challenge = challenge
        self.response = response
        self.manifest_type = manifest_type
        self.mimetype = mimetype
        self.license_data = license_data
        self.wv_secure = wv_secure

    def do_check(self):
        return install_widevine()

def set_bandwidth_bin(bps):
    addon = get_ia_addon(install=False)
    if not addon:
        return

    addon_profile = xbmc.translatePath(addon.getAddonInfo('profile'))
    bin_path = os.path.join(addon_profile, 'bandwidth.bin')

    if not os.path.exists(addon_profile):
        os.makedirs(addon_profile)

    value = bps / 8
    with open(bin_path, 'wb') as f:
        f.write(struct.pack('d', value))

    log.debug('IA Set Bandwidth Bin: {} bps'.format(bps))

def set_settings(settings):
    addon = get_ia_addon(install=False)
    if not addon:
        return

    log.debug('IA Set Settings: {}'.format(settings))

    for key in settings:
        addon.setSetting(key, str(settings[key]))

def get_settings(keys):
    addon = get_ia_addon(install=False)
    if not addon:
        return None

    settings = {}
    for key in keys:
        settings[key] = addon.getSetting(key)

    return settings

def open_settings():
    ia_addon = get_ia_addon()
    if ia_addon:
        ia_addon.openSettings()

def require_version(required_version, required=False):
    ia_addon = get_ia_addon(required=required)
    if not ia_addon:
        return False

    current_version = ia_addon.getAddonInfo('version')
    result = LooseVersion(current_version) >= LooseVersion(required_version)
    if required and not result:
        raise InputStreamError(_(_.IA_VERSION_REQUIRED, required=required_version, current=current_version))

    return ia_addon if result else False

def supports_arm64tls():
    try:
        return int(os.environ['LIBC_WIDEVINE_PATCHLEVEL']) >= 1
    except KeyError:
        pass

    try:
        return 'arm64tls' in subprocess.check_output(['ldd', '--version'], stderr=subprocess.STDOUT).decode('utf-8').split('\n')[0].lower()
    except Exception as e:
        log.exception(e)
        return False

def install_widevine(reinstall=False):
    DST_FILES = {
        'Linux': 'libwidevinecdm.so',
        'Darwin': 'libwidevinecdm.dylib',
        'IOS': 'libwidevinecdm.dylib',
        'TVOS': 'libwidevinecdm.dylib',
        'Windows': 'widevinecdm.dll',
        'UWP': 'widevinecdm.dll',
    }

    if KODI_VERSION < 18:
        raise InputStreamError(_.IA_KODI18_REQUIRED)

    ia_addon = require_version(IA_WV_MIN_VER, required=True)
    system, arch = get_system_arch()

    if system == 'Android':
        return True

    if system not in DST_FILES:
        raise InputStreamError(_(_.IA_NOT_SUPPORTED, system=system, arch=arch, kodi_version=KODI_VERSION))

    userdata = Userdata(COMMON_ADDON)
    decryptpath = xbmc.translatePath(ia_addon.getSetting('DECRYPTERPATH') or ia_addon.getAddonInfo('profile'))
    wv_path = os.path.join(decryptpath, DST_FILES[system])
    installed = md5sum(wv_path)
    last_check = int(userdata.get('_wv_last_check', 0))

    if not installed:
        if system == 'UWP':
            raise InputStreamError(_.IA_UWP_ERROR)

        elif system == 'IOS':
            raise InputStreamError(_.IA_IOS_ERROR)

        elif system == 'TVOS':
            raise InputStreamError(_.IA_TVOS_ERROR)

        elif system == 'Linux' and arch == 'arm64':
            raise InputStreamError(_.IA_AARCH64_ERROR)

        elif arch == 'armv6':
            raise InputStreamError(_.IA_ARMV6_ERROR)

        else:
            reinstall = True

    if not reinstall and time.time() - last_check < IA_CHECK_EVERY:
        return True

    ## DO INSTALL ##
    userdata.set('_wv_last_check', int(time.time()))

    widevine = Session().gz_json(IA_MODULES_URL)['widevine']
    wv_versions = widevine['platforms'].get(system + arch, [])

    if not wv_versions:
        raise InputStreamError(_(_.IA_NOT_SUPPORTED, system=system, arch=arch, kodi_version=KODI_VERSION))

    current = None
    latest = None
    tls_min_version = LooseVersion('4.10.2252.0')
    for wv in wv_versions:
        wv['compatible'] = True
        wv['label'] = str(wv['ver'])
        wv['ver'] = LooseVersion(wv['ver'])
        wv['confirm'] = wv.get('confirm', None)
        wv['notes'] = wv.get('notes', None)

        if 'arm' in arch.lower() and wv['ver'] >= tls_min_version and not supports_arm64tls():
            wv['compatible'] = False
            wv['label'] = _(_.WV_UNSUPPORTED_OS, label=wv['label'])
            if not wv['confirm']:
                wv['confirm'] = _.WV_UNSUPPORTED_OS_CONFIRM

        if wv.get('revoked'):
            wv['compatible'] = False
            wv['label'] = _(_.WV_REVOKED, label=wv['label'])
            if not wv['confirm']:
                wv['confirm'] = _.WV_REVOKED_CONFIRM

        if not latest:
            latest = wv
            if wv['compatible']:
                wv['label'] = _(_.WV_LATEST, label=wv['label'])

        if wv['md5'] == installed:
            current = wv
            wv['label'] = _(_.WV_INSTALLED, label=wv['label'])

        if wv['notes']:
            wv['label'] = u'{}\n{}'.format(wv['label'], wv['notes'])

    latest = wv_versions[0]
    latest_known = userdata.get('_wv_latest_md5')
    userdata.set('_wv_latest_md5', latest['md5'])

    if not reinstall and (installed == latest['md5'] or latest['md5'] == latest_known):
        return True

    if installed and not current:
        wv_versions.insert(0, {
            'ver': installed[:6],
            'label': _(_.WV_INSTALLED, label=_(_.WV_UNKNOWN, label=str(installed[:6]))),
        })

    while True:
        index = gui.select(_.SELECT_WV_VERSION, options=[x['label'] for x in wv_versions])
        if index < 0:
            return False

        selected = wv_versions[index]
        if selected.get('confirm') and not gui.yes_no(selected['confirm']):
            continue

        if 'src' in selected:
            url = widevine['base_url'] + selected['src']
            if not _download(url, wv_path, selected['md5']):
                continue

        break

    if system == 'Linux':
        try:
            subprocess.check_output('apt-get -y install libnss3 || sudo apt-get -y install libnss3', shell=True)
            log.debug('libnss3 installed')
        except Exception as e:
            log.debug('libnss3 failed to install')

    gui.ok(_(_.IA_WV_INSTALL_OK, version=selected['ver']))

    return True

def _download(url, dst_path, md5=None):
    dir_path = os.path.dirname(dst_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    filename   = url.split('/')[-1]
    downloaded = 0

    if os.path.exists(dst_path):
        if md5 and md5sum(dst_path) == md5:
            log.debug('MD5 of local file {} same. Skipping download'.format(filename))
            return True
        else:
            remove_file(dst_path)

    with gui.progress(_(_.IA_DOWNLOADING_FILE, url=filename), heading=_.IA_WIDEVINE_DRM) as progress:
        resp = Session().get(url, stream=True)
        if resp.status_code != 200:
            raise InputStreamError(_(_.ERROR_DOWNLOADING_FILE, filename=filename))

        total_length = float(resp.headers.get('content-length', 1))

        with open(dst_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                downloaded += len(chunk)
                percent = int(downloaded*100/total_length)

                if progress.iscanceled():
                    progress.close()
                    resp.close()

                progress.update(percent)

    if progress.iscanceled():
        remove_file(dst_path)
        return False

    checksum = md5sum(dst_path)
    if checksum != md5:
        remove_file(dst_path)
        raise InputStreamError(_(_.MD5_MISMATCH, filename=filename, local_md5=checksum, remote_md5=md5))

    return True
