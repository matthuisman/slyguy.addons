import sys
import json
import traceback
import time
from contextlib import contextmanager

from six.moves.urllib_parse import urlparse
from kodi_six import xbmcgui, xbmc

from . import settings
from .constants import *
from .router import add_url_args
from .language import _
from .smart_urls import get_dns_rewrites
from .util import fix_url, set_kodi_string, hash_6, get_url_headers, get_headers_from_url
from .session import Session


if KODI_VERSION >= 20:
    from .listitem import ListItemInfoTag

def _make_heading(heading=None):
    return heading if heading else ADDON_NAME

def refresh():
    set_kodi_string('slyguy_refresh', '1')
    xbmc.executebuiltin('Container.Refresh')

def redirect(location):
    xbmc.executebuiltin('Container.Update({},replace)'.format(location))

def get_view_id():
    return xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()

def get_art_url(url, headers=None):
    if not url or not url.lower().startswith(('http', 'plugin')):
        return url

    if url.lower().startswith('http'):
        url = url.replace(' ', '%20')

    _headers = {'user-agent': DEFAULT_USERAGENT}
    _headers.update(headers or {})
    _headers.update(get_headers_from_url(url))

    if settings.common_settings.getBool('proxy_enabled', True):
        proxy_path = settings.common_settings.get('_proxy_path')
        if proxy_path:
            _headers.update({'session_type': 'art', 'session_addonid': ADDON_ID})
            if not url.lower().startswith(proxy_path.lower()):
                url = proxy_path + url

    return url.split('|')[0] + '|' + get_url_headers(_headers)

def exception(heading=None):
    if not heading:
        heading = _(_.PLUGIN_EXCEPTION, addon=ADDON_NAME, version=ADDON_VERSION, common_version=COMMON_ADDON.getAddonInfo('version'))

    exc_type, exc_value, exc_traceback = sys.exc_info()

    tb = []

    include = [ADDON_ID,  os.path.join(COMMON_ADDON_ID, 'resources', 'modules', 'slyguy'), os.path.join(COMMON_ADDON_ID, 'resources', 'lib')]
    fline = True
    for trace in reversed(traceback.extract_tb(exc_traceback)):
        trace = list(trace)
        if fline:
            trace[0] = os.path.basename(trace[0])
            tb.append(trace)
            fline = False
            continue

        for _id in include:
            if _id in trace[0]:
                trace[0] = os.path.basename(trace[0])
                tb.append(trace)

    error = '{}\n{}'.format(''.join(traceback.format_exception_only(exc_type, exc_value)), ''.join(traceback.format_list(tb)))

    text(error, heading=heading)

class Progress(object):
    def __init__(self, message='', heading=None, percent=0, background=False):
        heading = _make_heading(heading)
        self._background = background

        if self._background:
            self._dialog = xbmcgui.DialogProgressBG()
        else:
            self._dialog = xbmcgui.DialogProgress()

        self._dialog.create(heading, *self._get_args(message))
        self.update(percent)

    def update(self, percent=0, message=None):
        self._dialog.update(int(percent), *self._get_args(message))

    def _get_args(self, message):
        if self._background or message is None or KODI_VERSION > 18:
            args = [message]
        else:
            args = message.split('\n')[:3]
            while len(args) < 3:
                args.append(' ')

        return args

    def iscanceled(self):
        if self._background:
            return self._dialog.isFinished()
        else:
            return self._dialog.iscanceled()

    def close(self):
        self._dialog.close()

def progressbg(message='', heading=None, percent=0):
    heading = _make_heading(heading)

    dialog = xbmcgui.DialogProgressBG()
    dialog.create(heading, message)
    dialog.update(int(percent))

    return dialog

@contextmanager
def busy():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

@contextmanager
def progress(message='', heading=None, percent=0, background=False):
    dialog = Progress(message=message, heading=heading, percent=percent, background=background)

    try:
        yield dialog
    finally:
        dialog.close()

def notification(message, heading=None, icon=None, time=3000, sound=False):
    heading = _make_heading(heading)
    icon = ADDON_ICON if not icon else icon
    xbmcgui.Dialog().notification(heading, message, get_art_url(icon), time, sound)

def select(heading=None, options=None, autoclose=None, multi=False, **kwargs):
    heading = _make_heading(heading)
    options = options or []

    if KODI_VERSION < 18:
        kwargs.pop('preselect', None) # preselect breaks cancel in 17
        if KODI_VERSION < 17:
            kwargs.pop('useDetails', None) # useDetails added in 17

    if autoclose:
        kwargs['autoclose'] = autoclose

    _options = []
    for option in options:
        if issubclass(type(option), Item):
            option = option.label if KODI_VERSION < 17 else option.get_li()

        _options.append(option)

    if multi:
        return xbmcgui.Dialog().multiselect(heading, _options, **kwargs)
    else:
        return xbmcgui.Dialog().select(heading, _options, **kwargs)

def input(message, default='', hide_input=False, **kwargs):
    if hide_input:
        kwargs['option'] = xbmcgui.ALPHANUM_HIDE_INPUT

    return xbmcgui.Dialog().input(message, default, **kwargs)

def numeric(message, default='', type=0, **kwargs):
    try:
        return int(xbmcgui.Dialog().numeric(type, message, defaultt=str(default), **kwargs))
    except:
        return None

def error(message, heading=None):
    heading = heading or _(_.PLUGIN_ERROR, addon=ADDON_NAME)
    return ok(message, heading)

def ok(message, heading=None):
    heading = _make_heading(heading)
    return xbmcgui.Dialog().ok(heading, message)

def text(message, heading=None, **kwargs):
    heading = _make_heading(heading)
    return xbmcgui.Dialog().textviewer(heading, message)

def yes_no(message, heading=None, autoclose=None, **kwargs):
    heading = _make_heading(heading)

    if autoclose:
        kwargs['autoclose'] = autoclose

    return xbmcgui.Dialog().yesno(heading, message, **kwargs)

def info(item):
    #playing python path via info dialog fixed in 19
    if KODI_VERSION < 19:
        item.path = None
    dialog = xbmcgui.Dialog()
    dialog.info(item.get_li())

def context_menu(options):
    if KODI_VERSION < 17:
        return select(options=options)

    dialog = xbmcgui.Dialog()
    return dialog.contextmenu(options)

class Item(object):
    def __init__(self, id=None, label='', path=None, playable=False, info=None, context=None,
            headers=None, cookies=None, properties=None, is_folder=None, art=None, inputstream=None,
            video=None, audio=None, subtitles=None, use_proxy=True, specialsort=None, custom=None, proxy_data=None,
            resume_from=None, force_resume=False, dns_rewrites=None):

        self.id          = id
        self.label       = label
        self.path        = path
        self.info        = dict(info or {})
        self.headers     = dict(headers or {})
        self.cookies     = dict(cookies or {})
        self.properties  = dict(properties or {})
        self.art         = dict(art or {})
        self.video       = dict(video or {})
        self.audio       = dict(audio or {})
        self.context     = list(context or [])
        self.subtitles   = subtitles or []
        self.playable    = playable
        self.inputstream = inputstream
        self.proxy_data  = proxy_data or {}
        self.dns_rewrites = dns_rewrites or {}
        self.mimetype    = None
        self._is_folder  = is_folder
        self.specialsort = specialsort #bottom, top
        self.custom      = custom
        self.use_proxy   = use_proxy
        self.resume_from = resume_from
        self.force_resume = force_resume

    def update(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    @property
    def is_folder(self):
        return not self.playable if self._is_folder == None else self._is_folder

    @is_folder.setter
    def is_folder(self, value):
        self._is_folder = value

    def get_li(self, playing=False):
        proxy_path = settings.common_settings.get('_proxy_path')

        if KODI_VERSION < 18:
            li = xbmcgui.ListItem()
        else:
            li = xbmcgui.ListItem(offscreen=True)

        info = self.info.copy()
        if self.label:
            li.setLabel(self.label)

        if info:
            if not info.get('title') and self.label and info.get('mediatype'):
                info['title'] = self.label

            if info.get('mediatype') == 'movie':
                info.pop('season', None)
                info.pop('episode', None)
                info.pop('tvshowtitle', None)

            year = info.get('year') or ''
            aired = info.get('aired') or ''
            premiered = info.get('premiered') or ''
            date_added = info.get('dateadded') or ''
            date = info.get('date') or ''

            if not aired and premiered:
                info['aired'] = aired = premiered

            if year and not aired:
                info['aired'] = aired = '{}-01-01'.format(year)

            if not premiered and aired:
                info['premiered'] = premiered = aired

            if not year and len(aired) >= 4:
                info['year'] = year = aired[0:4]

            if not date_added and aired:
                info['dateadded'] = date_added = '{} 12:00:00'.format(aired)

            if not date and aired:
                info['date'] = aired

        # there is a kodi bug that wont resume from favourites if you dont call one of a methods on the li
        # see https://forum.kodi.tv/showthread.php?tid=374491&pid=3167595#pid3167595
        # Therefore, always calling the below even with empty info
        if KODI_VERSION >= 20:
            if info.get('genre'):
                if not isinstance(info['genre'], list):
                    info['genre'] = [info['genre']]
            else:
                info.pop('genre', None)

            if info.get('date'):
                try: li.setDateTime(info.pop('date'))
                except: pass
            #TODO: do own 20+ wrapper layer
            ListItemInfoTag(li, 'video').set_info(info)
        else:
            if info.get('date'):
                try: info['date'] = '{}.{}.{}'.format(info['date'][8:10], info['date'][5:7], info['date'][0:4])
                except: pass

            if info.get('cast'):
                try: info['cast'] = [(member['name'], member['role']) for member in info['cast']]
                except: pass
            li.setInfo('video', info)

        if self.specialsort:
            li.setProperty('specialsort', self.specialsort)

        if self.video:
            li.addStreamInfo('video', self.video)
        if self.audio:
            li.addStreamInfo('audio', self.audio)

        if self.art:
            defaults = {
                'poster': 'thumb',
                'landscape': 'thumb',
                'icon': 'thumb',
            }

            art = {}
            for key in self.art:
                art[key] = get_art_url(self.art[key])

            for key in defaults:
                if key not in art:
                    art[key] = art.get(defaults[key])

            li.setArt(art)

        if self.playable and not playing:
            li.setProperty('IsPlayable', 'true')
            if self.path:
                self.path = add_url_args(self.path, _play=1)

        if self.context:
            li.addContextMenuItems(self.context)

        if self.resume_from is not None:
            # Setting this on Kodi 18 or below removes all list item data (fixed in 19)
            self.properties['ResumeTime'] = self.resume_from
            self.properties['TotalTime'] = 1

        if not self.force_resume and len(sys.argv) > 3 and sys.argv[3].lower() == 'resume:true':
            self.properties.pop('ResumeTime', None)
            self.properties.pop('TotalTime', None)

        for key in self.properties:
            li.setProperty(key, u'{}'.format(self.properties[key]))

        # Kodi before 19 set referer header on redirect
        if KODI_VERSION < 19:
            if 'referer' not in [x.lower() for x in self.headers]:
                self.headers['referer'] = '%20'

        headers = get_url_headers(self.headers, self.cookies)
        mimetype = self.mimetype
        if not mimetype and self.inputstream:
            mimetype = self.inputstream.mimetype

        def is_http(url):
            return url.lower().startswith('http://') or url.lower().startswith('https://')

        def get_url(url):
            _url = url.lower()

            if os.path.exists(xbmc.translatePath(url)) or _url.startswith('special://') or _url.startswith('plugin://') or (is_http(_url) and self.use_proxy and not _url.startswith(proxy_path)) and settings.common_settings.getBool('proxy_enabled', True):
                url = u'{}{}'.format(proxy_path, url)

            return url

        def redirect_url(url):
            parse = urlparse(url.lower())
            if parse.netloc in REDIRECT_HOSTS and is_http(url):
                url = Session().head(url).headers.get('location') or url
            return url

        license_url = None
        if self.inputstream and self.inputstream.check():
            if KODI_VERSION < 19:
                li.setProperty('inputstreamaddon', self.inputstream.addon_id)
            else:
                li.setProperty('inputstream', self.inputstream.addon_id)

            # li.setProperty('inputstream', 'inputstream.ffmpegdirect')
            # li.setProperty('mimetype', 'application/x-mpegURL')
            # li.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
            # li.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
            # li.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
            # li.setProperty('inputstream.ffmpegdirect.open_mode', 'curl')

            self.inputstream.set_setting('HDCPOVERRIDE', 'true')

            if self.inputstream.server_certificate and not self.inputstream.flags:
                self.inputstream.flags = 'persistent_storage'

            li.setProperty('{}.manifest_type'.format(self.inputstream.addon_id), self.inputstream.manifest_type)

            if self.inputstream.license_type:
                li.setProperty('{}.license_type'.format(self.inputstream.addon_id), self.inputstream.license_type)

            if self.inputstream.flags:
                li.setProperty('{}.license_flags'.format(self.inputstream.addon_id), self.inputstream.flags)

            if self.inputstream.server_certificate:
                li.setProperty('{}.server_certificate'.format(self.inputstream.addon_id), self.inputstream.server_certificate)

            if headers:
                li.setProperty('{}.stream_headers'.format(self.inputstream.addon_id), headers)
                li.setProperty('{}.manifest_headers'.format(self.inputstream.addon_id), headers)

            if 'original_language' in self.proxy_data:
                li.setProperty('{}.original_audio_language'.format(self.inputstream.addon_id), self.proxy_data['original_language'])

            if self.inputstream.license_key:
                license_url = self.inputstream.license_key
                license_headers = get_url_headers(self.inputstream.license_headers) if self.inputstream.license_headers else headers
                li.setProperty('{}.license_key'.format(self.inputstream.addon_id), u'{url}|Content-Type={content_type}{headers}|{challenge}|{response}'.format(
                    url = get_url(redirect_url(fix_url(self.inputstream.license_key))),
                    content_type = self.inputstream.content_type,
                    headers = '&' + license_headers if license_headers else '',
                    challenge = self.inputstream.challenge,
                    response = self.inputstream.response,
                ))
                #If we need secure wv and IA is from kodi 18 or below, we need to force secure decoder
                if self.inputstream.wv_secure and KODI_VERSION < 19:
                    li.setProperty('{}.license_flags'.format(self.inputstream.addon_id), 'force_secure_decoder')
            elif headers:
                li.setProperty('{}.license_key'.format(self.inputstream.addon_id), u'|{}'.format(headers))

            if self.inputstream.license_data:
                li.setProperty('{}.license_data'.format(self.inputstream.addon_id), self.inputstream.license_data)

            for key in self.inputstream.properties:
                li.setProperty(self.inputstream.addon_id+'.'+key, self.inputstream.properties[key])
        else:
            self.inputstream = None

        def make_sub(url, language='unk', mimetype='', forced=False, impaired=False):
            if os.path.exists(xbmc.translatePath(url)):
                return url

            ## using dash, we can embed subs
            if self.inputstream and self.inputstream.manifest_type == 'mpd':
                if mimetype not in ('application/ttml+xml', 'text/vtt') and not url.lower().startswith('plugin://'):
                    ## can't play directly - covert to webvtt
                    proxy_data['middleware'][url] = {'type': MIDDLEWARE_CONVERT_SUB}
                    mimetype = 'text/vtt'

                proxy_data['subtitles'].append([mimetype, language, url, 'forced' if forced else None, 'impaired' if impaired else None])
                return None

            ## only srt or webvtt (text/) supported
            if not mimetype.startswith('text/') and not url.lower().startswith('plugin://'):
                proxy_data['middleware'][url] = {'type': MIDDLEWARE_CONVERT_SUB}
                mimetype = 'text/vtt'

            proxy_url = '{}{}.srt'.format(language, '.forced' if forced else '')
            proxy_data['path_subs'][proxy_url] = url

            return u'{}{}'.format(proxy_path, proxy_url)

        if self.path and playing:
            self.path = redirect_url(fix_url(self.path))
            final_path = get_url(self.path)
            if is_http(final_path):
                if not mimetype:
                    parse = urlparse(self.path.lower())
                    if parse.path.endswith('.m3u') or parse.path.endswith('.m3u8'):
                        mimetype = 'application/vnd.apple.mpegurl'
                    elif parse.path.endswith('.mpd'):
                        mimetype = 'application/dash+xml'
                    elif parse.path.endswith('.ism'):
                        mimetype = 'application/vnd.ms-sstr+xml'

                proxy_data = {
                    'manifest': self.path,
                    'slug': '{}-{}'.format(ADDON_ID, sys.argv[2]),
                    'license_url': license_url,
                    'session_id': hash_6(time.time()),
                    'audio_whitelist': settings.get('audio_whitelist', ''),
                    'subs_whitelist':  settings.get('subs_whitelist', ''),
                    'audio_description': settings.getBool('audio_description', True),
                    'subs_forced': settings.getBool('subs_forced', True),
                    'subs_non_forced': settings.getBool('subs_non_forced', True),
                    'remove_framerate': False,
                    'subtitles': [],
                    'path_subs': {},
                    'addon_id': ADDON_ID,
                    'quality': QUALITY_DISABLED,
                    'middleware': {},
                    'type': None,
                    'skip_next_channel': settings.common_settings.getBool('skip_next_channel', False),
                    'h265': settings.common_settings.getBool('h265', False),
                    'vp9': settings.common_settings.getBool('vp9', False),
                    'av1': settings.common_settings.getBool('av1', False),
                    'hdr10': settings.common_settings.getBool('hdr10', False),
                    'dolby_vision': settings.common_settings.getBool('dolby_vision', False),
                    'dolby_atmos': settings.common_settings.getBool('dolby_atmos', False),
                    'ac3': settings.common_settings.getBool('ac3', False),
                    'ec3': settings.common_settings.getBool('ec3', False),
                    'verify': settings.common_settings.getBool('verify_ssl', True),
                    'timeout': settings.common_settings.getInt('http_timeout', 30),
                    'dns_rewrites': get_dns_rewrites(self.dns_rewrites),
                    'proxy_server': settings.get('proxy_server') or settings.common_settings.get('proxy_server'),
                    'max_width': settings.common_settings.getInt('max_width', 0),
                    'max_height': settings.common_settings.getInt('max_width', 0),
                    'max_channels': settings.common_settings.getInt('max_channels', 0),
                }

                #######################################
                ## keep old setting values working until new settings system implemented
                legacy_map = {
                    'vp9': [],
                    'av1': [],
                    'h265': ['hevc','enable_h265',],
                    'hdr10': ['enable_hdr',],
                    'dolby_vision': [],
                    'dolby_atmos': ['atmos_enabled',],
                    'ac3': ['ac3_enabled',],
                    'ec3': ['ec3_enabled',],
                }

                for key in legacy_map:
                    #add ourself so addon can override common
                    legacy_map[key].append(key)
                    for old_key in legacy_map[key]:
                        val = settings.getBool(old_key, None)
                        if val is not None:
                            proxy_data[key] = val
                            break
                #########################################

                if mimetype == 'application/vnd.apple.mpegurl':
                    proxy_data['type'] = 'm3u8'
                elif mimetype == 'application/dash+xml':
                    proxy_data['type'] = 'mpd'

                if settings.common_settings.getBool('ignore_display_resolution', False) is False:
                    screen_width = int(xbmc.getInfoLabel('System.ScreenWidth') or 0)
                    screen_height = int(xbmc.getInfoLabel('System.ScreenHeight') or 0)
                    if screen_width:
                        if not proxy_data['max_width']:
                            proxy_data['max_width'] = screen_width
                        else:
                            proxy_data['max_width'] = min(screen_width, proxy_data['max_width'])
                    if screen_height:
                        if not proxy_data['max_height']:
                            proxy_data['max_height'] = screen_height
                        else:
                            proxy_data['max_height'] = min(screen_height, proxy_data['max_height'])

                proxy_data.update(self.proxy_data)

                for key in ['default_language', 'default_subtitle']:
                    value = settings.get(key, '')
                    if value:
                        proxy_data[key] = value

                if self.subtitles:
                    subs = []
                    for sub in self.subtitles:
                        if type(sub) == str:
                            sub = make_sub(sub)
                        elif type(sub) == list:
                            sub = make_sub(*sub)
                        else:
                            sub = make_sub(**sub)
                        if sub:
                            subs.append(sub)

                    li.setSubtitles(list(subs))

                set_kodi_string('_slyguy_proxy_data', json.dumps(proxy_data))

                if headers and '|' not in final_path:
                    final_path = u'{}|{}'.format(final_path, headers)

            self.path = final_path

        if mimetype:
            li.setMimeType(mimetype)
            li.setContentLookup(False)

        if self.path:
            li.setPath(self.path)

        return li

    def play(self):
        li = self.get_li()
        xbmc.Player().play(self.path, li)
