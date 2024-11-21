import os
import sys
import hashlib
import shutil
import platform
import base64
import struct
import codecs
import json
import io
import gzip
import re
import threading
import socket
import binascii
from contextlib import closing

import requests
from kodi_six import xbmc, xbmcgui, xbmcaddon, xbmcvfs
from six.moves import queue, range
from six.moves.urllib.parse import urlparse, urlunparse, quote, parse_qsl
from requests.models import PreparedRequest
from six import PY2

if sys.version_info >= (3, 8):
    import html
else:
    from six.moves.html_parser import HTMLParser
    html = HTMLParser()

from slyguy import log, _
from slyguy.exceptions import Error
from slyguy.constants import *


def run_plugin(path, wait=False):
    if wait:
        dirs, files = xbmcvfs.listdir(path)
        return dirs, files
    else:
        xbmc.executebuiltin('RunPlugin({})'.format(path))
        return [], []

def fix_url(url):
    parse = urlparse(url)
    parse = parse._replace(path=re.sub('/{2,}','/',parse.path))
    return urlunparse(parse)

def add_url_args(url, params=None):
    req = PreparedRequest()
    req.prepare_url(url, params)
    return req.url

def check_port(port=0, default=False):
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('127.0.0.1', port))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
    except:
        return default

def kodi_db(name):
    options = []
    db_dir = xbmc.translatePath('special://database')

    for file in os.listdir(db_dir):
        db_path = os.path.join(db_dir, file)

        result = re.match(r'{}([0-9]+)\.db'.format(name.lower()), file.lower())
        if result:
            options.append([db_path, int(result.group(1))])

    options = sorted(options, key=lambda x: x[1], reverse=True)

    if options:
        return options[0][0]
    else:
        return None

def async_tasks(tasks, workers=DEFAULT_WORKERS, raise_on_error=True):
    def worker():
        while not task_queue.empty():
            task, index = task_queue.get_nowait()
            try:
                resp_queue.put([task(), index])
            except Exception as e:
                resp_queue.put([e, index])
            finally:
                task_queue.task_done()

    task_queue = queue.Queue()
    resp_queue = queue.Queue()

    for i in range(len(tasks)):
        task_queue.put([tasks[i], i])

    threads = []
    num_workers = min(workers, len(tasks))
    log.debug('Starting {} workers'.format(num_workers))
    for i in range(num_workers):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        threads.append(thread)

    results = []
    exception = None
    for i in range(len(tasks)):
        result = resp_queue.get()

        if raise_on_error and isinstance(result[0], Exception):
            with task_queue.mutex:
                task_queue.queue.clear()

            exception = result[0]
            break

        results.append(result)

    for thread in threads:
        thread.join()

    if exception:
        raise exception

    return [x[0] for x in sorted(results, key=lambda x: x[1])]

def get_addon(addon_id, required=False, install=True):
    try:
        try: return xbmcaddon.Addon(addon_id)
        except: pass

        if install:
            xbmc.executebuiltin('InstallAddon({})'.format(addon_id), True)

        kodi_rpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True}, raise_on_error=True)

        return xbmcaddon.Addon(addon_id)
    except:
        if required:
            raise Error(_(_.ADDON_REQUIRED, addon_id=addon_id))
        else:
            return None

def require_country(required=None, _raise=False):
    if not required:
        return ''

    required = required.upper()
    country  = user_country()
    if country and country != required:
        msg = _(_.GEO_COUNTRY_ERROR, required=required, current=country)
        if _raise:
            raise Error(msg)
        else:
            return msg

    return ''

def user_country():
    try:
        country = requests.get('http://ip-api.com/json/?fields=countryCode').json()['countryCode'].upper()
        log.debug('fetched user country: {}'.format(country))
        return country
    except:
        log.debug('Unable to get users country')
        return ''

def FileIO(file_name, method, chunksize=CHUNK_SIZE):
    if xbmc.getCondVisibility('System.Platform.Android'):
        file_obj = io.FileIO(file_name, method)
        if method.startswith('r'):
            return io.BufferedReader(file_obj, buffer_size=chunksize)
        else:
            return io.BufferedWriter(file_obj, buffer_size=chunksize)
    else:
        return open(file_name, method, chunksize)

def same_file(path_a, path_b):
    if path_a.lower().strip() == path_b.lower().strip():
        return True

    stat_a = os.stat(path_a) if os.path.isfile(path_a) else None
    if not stat_a:
        return False

    stat_b = os.stat(path_b) if os.path.isfile(path_b) else None
    if not stat_b:
        return False

    return (stat_a.st_dev == stat_b.st_dev) and (stat_a.st_ino == stat_b.st_ino) and (stat_a.st_mtime == stat_b.st_mtime)

def safe_copy(src, dst, del_src=False):
    src = xbmc.translatePath(src)
    dst = xbmc.translatePath(dst)

    if not xbmcvfs.exists(src) or same_file(src, dst):
        return

    if xbmcvfs.exists(dst):
        if xbmcvfs.delete(dst):
            log.debug('Deleted: {}'.format(dst))
        else:
            log.debug('Failed to delete: {}'.format(dst))

    if xbmcvfs.copy(src, dst):
        log.debug('Copied: {} > {}'.format(src, dst))
    else:
        log.debug('Failed to copy: {} > {}'.format(src, dst))

    if del_src:
        xbmcvfs.delete(src)

def gzip_extract(in_path, chunksize=CHUNK_SIZE, raise_error=True):
    log.debug('Gzip Extracting: {}'.format(in_path))
    out_path = in_path + '_extract'

    try:
        with FileIO(out_path, 'wb') as f_out:
            with FileIO(in_path, 'rb') as in_obj:
                with gzip.GzipFile(fileobj=in_obj) as f_in:
                    shutil.copyfileobj(f_in, f_out, length=chunksize)
    except Exception as e:
        remove_file(out_path)
        if raise_error:
            raise
        log.exception(e)
        return False
    else:
        remove_file(in_path)
        shutil.move(out_path, in_path)
        return True

def xz_extract(in_path, chunksize=CHUNK_SIZE, raise_error=True):
    if PY2:
        raise Error(_.XZ_ERROR)

    import lzma

    log.debug('XZ Extracting: {}'.format(in_path))
    out_path = in_path + '_extract'

    try:
        with FileIO(out_path, 'wb') as f_out:
            with FileIO(in_path, 'rb') as in_obj:
                with lzma.LZMAFile(filename=in_obj) as f_in:
                    shutil.copyfileobj(f_in, f_out, length=chunksize)
    except Exception as e:
        remove_file(out_path)
        if raise_error:
            raise
        log.exception(e)
        return False
    else:
        remove_file(in_path)
        shutil.move(out_path, in_path)
        return True

def load_json(filepath, encoding='utf8', raise_error=True):
    try:
        with codecs.open(filepath, 'r', encoding='utf8') as f:
            return json.load(f)
    except:
        if raise_error:
            raise
        else:
            return False

def save_json(filepath, data, raise_error=True, pretty=False, **kwargs):
    _kwargs = {'ensure_ascii': False}

    if pretty:
        _kwargs['indent'] = 4
        _kwargs['sort_keys'] = True
        _kwargs['separators'] = (',', ': ')

    if PY2:
        _kwargs['encoding'] = 'utf8'

    _kwargs.update(kwargs)

    try:
        with codecs.open(filepath, 'w', encoding='utf8') as f:
            f.write(json.dumps(data, **_kwargs))

        return True
    except:
        if raise_error:
            raise
        else:
            return False

def jwt_data(token):
    b64_string = token.split('.')[1]
    b64_string += "=" * ((4 - len(b64_string) % 4) % 4) #fix padding
    return json.loads(base64.b64decode(b64_string))

def set_kodi_string(key, value=''):
    xbmcgui.Window(10000).setProperty(key, u"{}".format(value))

def get_kodi_string(key, default=''):
    value = xbmcgui.Window(10000).getProperty(key)
    return value or default

def get_kodi_setting(key, default=None):
    data = kodi_rpc('Settings.GetSettingValue', {'setting': key})
    return data.get('value', default)

def set_kodi_setting(key, value):
    return kodi_rpc('Settings.SetSettingValue', {'setting': key, 'value': value})

def kodi_rpc(method, params=None, raise_on_error=False):
    try:
        payload = {'jsonrpc':'2.0', 'id':1}
        payload.update({'method': method})
        if params:
            payload['params'] = params

        data = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
        if 'error' in data:
            raise Exception('Kodi RPC "{} {}" returned Error: "{}"'.format(method, params or '', data['error'].get('message')))

        return data['result']
    except Exception as e:
        if raise_on_error:
            raise
        else:
            return {}

def remove_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        return False
    else:
        return True

def hash_6(value, default=None, length=6):
    if not value:
        return default

    h = hashlib.md5(u'{}'.format(value).encode('utf8'))
    return base64.b64encode(h.digest()).decode('utf8')[:length]

def md5sum(filepath):
    if not os.path.exists(filepath):
        return None

    return hashlib.md5(open(filepath,'rb').read()).hexdigest()

## to find BCOV-POLICY. Open below url
## account_id / player_id / videoid can be found by right clicking player and selecting Player Information
## https://players.brightcove.net/{account_id}/{player_id}_default/index.html?videoId={videoid}
## then seach all files for policyKey

def process_brightcove(data):
    if type(data) != dict:
        log.error(data)
        try:
            msg = data[0]
        except IndexError:
            msg = _.NO_ERROR_MSG
        raise Error(_(_.NO_BRIGHTCOVE_SRC, error=msg))

    sources = []
    for source in data.get('sources', []):
        if not source.get('src'):
            continue

        # HLS
        if source.get('type') == 'application/x-mpegURL' and 'key_systems' not in source:
            sources.append({'source': source, 'type': 'hls', 'order_1': 1, 'order_2': int(source.get('ext_x_version', 0))})

        # MP4
        elif source.get('container') == 'MP4' and 'key_systems' not in source:
            sources.append({'source': source, 'type': 'mp4', 'order_1': 2, 'order_2': int(source.get('avg_bitrate', 0))})

        # Widevine cenc
        elif source.get('encryption_type', 'cenc') == 'cenc' and 'com.widevine.alpha' in source.get('key_systems', {}):
            sources.append({'source': source, 'type': 'widevine', 'mimetype': source['type'], 'order_1': 3, 'order_2': 0})

        elif source.get('type') == 'application/vnd.apple.mpegurl' and 'key_systems' not in source:
            sources.append({'source': source, 'type': 'hls', 'order_1': 1, 'order_2': 0})

    if not sources:
        raise Error(_.NO_BRIGHTCOVE_SRC)

    sources = sorted(sources, key = lambda x: (x['order_1'], -x['order_2']))
    source = sources[0]

    from . import plugin, inputstream

    if source['type'] == 'mp4':
        return plugin.Item(
            path = source['source']['src'],
            art = False,
        )
    elif source['type'] == 'hls':
        return plugin.Item(
            path = source['source']['src'],
            inputstream = inputstream.HLS(live=False, force=False),
            art = False,
        )
    elif source['type'] == 'widevine':
        return plugin.Item(
            path = source['source']['src'],
            inputstream = inputstream.Widevine(license_key=source['source']['key_systems']['com.widevine.alpha']['license_url'], mimetype=source['mimetype'], manifest_type='mpd' if source['mimetype'] == 'application/dash+xml' else 'hls'),
            art = False,
        )
    else:
        raise Error(_.NO_BRIGHTCOVE_SRC)

def get_system_arch():
    if xbmc.getCondVisibility('System.Platform.Android'):
        system = 'Android'
    elif xbmc.getCondVisibility('System.Platform.WebOS') or os.path.exists('/var/run/nyx/os_info.json'):
        system = 'WebOS'
    elif xbmc.getCondVisibility('System.Platform.UWP') or '4n2hpmxwrvr6p' in xbmc.translatePath('special://xbmc/'):
        system = 'UWP'
    elif xbmc.getCondVisibility('System.Platform.Windows'):
        system = 'Windows'
    elif xbmc.getCondVisibility('System.Platform.IOS'):
        system = 'IOS'
    elif xbmc.getCondVisibility('System.Platform.TVOS'):
        system = 'TVOS'
    elif xbmc.getCondVisibility('System.Platform.Darwin'):
        system = 'Darwin'
    elif xbmc.getCondVisibility('System.Platform.Linux') or xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
        system = 'Linux'
    else:
        system = platform.system()

    if system == 'Windows':
        arch = platform.architecture()[0].lower()
    else:
        try:
            arch = platform.machine().lower()
        except:
            arch = ''

    if 'aarch64' in arch or 'arm64' in arch:
        #64bit kernel with 32bit userland
        if (struct.calcsize("P") * 8) == 32:
            arch = 'armv7'
        else:
            arch = 'arm64'

    elif 'arm' in arch:
        if 'v6' in arch:
            arch = 'armv6'
        else:
            arch = 'armv7'

    elif arch == 'i686':
        arch = 'i386'

    if 'appletv' in arch:
        arch = 'arm64'

    log.debug('System: {}, Arch: {}'.format(system, arch))

    return system, arch

def cenc_init(data=None, uuid=None, kids=None, version=None):
    data = data or bytearray()
    uuid = uuid or WIDEVINE_UUID
    kids = kids or []

    length = len(data) + 32

    if version == 0:
        kids = []

    if kids:
        #each kid is 16 bytes (+ 4 for kid count)
        length += (len(kids) * 16) + 4

    init_data = bytearray(length)
    pos = 0

    # length (4 bytes)
    r_uint32 = struct.pack(">I", length)
    init_data[pos:pos+len(r_uint32)] = r_uint32
    pos += len(r_uint32)

    # pssh (4 bytes)
    init_data[pos:pos+len(r_uint32)] = WIDEVINE_PSSH
    pos += len(WIDEVINE_PSSH)

    # version (1 if kids else 0)
    r_uint32 = struct.pack("<I", 1 if kids else 0)
    init_data[pos:pos+len(r_uint32)] = r_uint32
    pos += len(r_uint32)

    # uuid (16 bytes)
    init_data[pos:pos+len(uuid)] = uuid
    pos += len(uuid)

    if kids:
        # kid count (4 bytes)
        r_uint32 = struct.pack(">I", len(kids))
        init_data[pos:pos+len(r_uint32)] = r_uint32
        pos += len(r_uint32)

        for kid in kids:
            # each kid (16 bytes)
            init_data[pos:pos+len(uuid)] = kid
            pos += len(kid)

    # length of data (4 bytes)
    r_uint32 = struct.pack(">I", len(data))
    init_data[pos:pos+len(r_uint32)] = r_uint32
    pos += len(r_uint32)

    # data (X bytes)
    init_data[pos:pos+len(data)] = data
    pos += len(data)

    return base64.b64encode(init_data).decode('utf8')

def parse_cenc_init(b64string):
    init_data = bytearray(base64.b64decode(b64string))
    pos = 0

    # length (4 bytes)
    r_uint32 = init_data[pos:pos+4]
    length, = struct.unpack(">I", r_uint32)
    pos += 4

    # pssh (4 bytes)
    r_uint32 = init_data[pos:pos+4]
    pssh, = struct.unpack(">I", r_uint32)
    pos += 4

    # version (4 bytes) (1 if kids else 0)
    r_uint32 = init_data[pos:pos+4]
    version, = struct.unpack("<I", r_uint32)
    pos += 4

    # uuid (16 bytes)
    uuid = init_data[pos:pos+16]
    pos += 16

    kids = []
    if version == 1:
        # kid count (4 bytes)
        r_uint32 = init_data[pos:pos+4]
        num_kids, = struct.unpack(">I", r_uint32)
        pos += 4

        for i in range(num_kids):
            # each kid (16 bytes)
            kids.append(init_data[pos:pos+16])
            pos += 16

    # length of data (4 bytes)
    r_uint32 = init_data[pos:pos+4]
    data_length, = struct.unpack(">I", r_uint32)
    pos += 4

    # data
    data = init_data[pos:pos+data_length]
    pos += data_length

    return uuid, version, data, kids

def cenc_version1to0(cenc):
    uuid, version, data, kids = parse_cenc_init(cenc)

    if version != 1 or not data or uuid != WIDEVINE_UUID:
        return cenc

    return cenc_init(data)

def replace_kids(cenc, kids, version0=False):
    uuid, version, old_data, old_kids = parse_cenc_init(cenc)

    old_data = binascii.hexlify(old_data).decode('utf8')
    if '1210' in old_data:
        pre_data = re.search('^([0-9a-z]*?)1210', old_data)
        pre_data = pre_data.group(1) if pre_data else ''

        old_data = old_data.replace(pre_data, '')
        for match in re.findall('1210[0-9a-z]{32}', old_data):
            old_data = old_data.replace(match, '')

        data = pre_data
        new_kids = []
        for kid in kids:
            kid = kid.replace('-', '').replace(' ','').strip() if kid else None
            if not kid or kid in data:
                continue

            data += '1210' + kid
            new_kids.append(bytearray.fromhex(kid))

        data += old_data
    else:
        data = old_data
        new_kids = kids

    return cenc_init(bytearray.fromhex(data), uuid, new_kids, 0 if version0 else version)

def pthms_to_seconds(duration):
    if not duration:
        return None

    keys = [['H', 3600], ['M', 60], ['S', 1]]

    seconds = 0
    duration = duration.lstrip('PT')
    for key in keys:
        if key[0] in duration:
            count, duration = duration.split(key[0])
            seconds += float(count) * key[1]

    return int(seconds)

def strip_html_tags(text):
    if not text:
        return ''

    text = re.sub(r'\([^\)]*\)', '', text)
    text = re.sub('<[^>]*>', '', text)
    text = html.unescape(text)
    return text

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def lang_allowed(lang, lang_list):
    if not lang_list:
        return True

    lang = lang.lower().strip()
    if not lang:
        return False

    for _lang in lang_list:
        _lang = _lang.lower().strip()
        if not _lang:
            continue

        if lang.startswith('!') and not lang.startswith(_lang[1:]):
            return True
        elif not lang.startswith('!') and lang.startswith(_lang):
            return True

    return False

def fix_language(language=None):
    if not language:
        return None

    language = language.strip()
    language = language.replace('_', '-')
    split = language.split('-')
    if len(split) > 1 and split[1].lower() == split[0].lower():
        return split[0].lower()

    # any non es-ES, treat as Spanish Argentina
    if len(split) > 1 and split[0].lower() == 'es':
        return 'es-AR'

    if language.lower() == 'pt-br':
        return 'pb'

    if language.lower() == 'cmn-tw':
        return 'zh-TW'

    if split[0].lower() == 'en':
        return 'en'

    if language.lower() in ('nb','nn'):
        return 'no'

    if language.lower() == 'ekk':
        return 'et'

    if language.lower() == 'lvs':
        return 'lv'

    if len(split[0]) == 2 and KODI_VERSION < 20:
        return split[0].lower()

    return language


def get_kodi_proxy():
    usehttpproxy = get_kodi_setting('network.usehttpproxy')
    if usehttpproxy is not True:
        return None

    try:
        httpproxytype = int(get_kodi_setting('network.httpproxytype'))
    except ValueError:
        httpproxytype = 0

    proxy_types = ['http', 'socks4', 'socks4a', 'socks5', 'socks5h']

    proxy = dict(
        scheme = proxy_types[httpproxytype] if 0 <= httpproxytype < 5 else 'http',
        server = get_kodi_setting('network.httpproxyserver'),
        port = get_kodi_setting('network.httpproxyport'),
        username = get_kodi_setting('network.httpproxyusername'),
        password = get_kodi_setting('network.httpproxypassword'),
    )

    if proxy.get('username') and proxy.get('password') and proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{username}:{password}@{server}:{port}'.format(**proxy)
    elif proxy.get('username') and proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{username}@{server}:{port}'.format(**proxy)
    elif proxy.get('server') and proxy.get('port'):
        proxy_address = '{scheme}://{server}:{port}'.format(**proxy)
    elif proxy.get('server'):
        proxy_address = '{scheme}://{server}'.format(**proxy)
    else:
        return None

    return proxy_address


def unique(sequence):
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]


def get_url_headers(headers=None, cookies=None):
    string = ''
    if headers:
        for key in headers:
            string += u'{0}={1}&'.format(key, quote(u'{}'.format(headers[key]).encode('utf8')))

    if cookies:
        string += 'Cookie='
        for key in cookies:
            string += u'{0}%3D{1}; '.format(key, quote(u'{}'.format(cookies[key]).encode('utf8')))

    return string.strip().strip('&')


def get_headers_from_url(url):
    split = url.split('|')
    if len(split) < 2:
        return {}

    headers = {}
    _headers = dict(parse_qsl(u'{}'.format(split[1]), keep_blank_values=True))
    for key in _headers:
        if _headers[key].startswith(' '):
            _headers[key] = u'%20{}'.format(_headers[key][1:])

        headers[key.lower()] = _headers[key]

    return headers


def makedirs(path):
    xbmcvfs.mkdirs(path)


def remove_duplicates(seq):
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]
