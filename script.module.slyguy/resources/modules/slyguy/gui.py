import sys
import json
import traceback
import time
from contextlib import contextmanager

from six.moves.urllib_parse import quote, urlparse
from kodi_six import xbmcgui, xbmc

from . import settings
from .constants import *
from .exceptions import GUIError
from .router import add_url_args, url_for
from .language import _
from .dns import get_dns_rewrites
from .util import url_sub, fix_url, set_kodi_string, hash_6

def _make_heading(heading=None):
    return heading if heading else ADDON_NAME

def refresh():
    set_kodi_string('slyguy_refresh', '1')
    xbmc.executebuiltin('Container.Refresh')

def redirect(location):
    xbmc.executebuiltin('Container.Update({},replace)'.format(location))

def exception(heading=None):
    if not heading:
        heading = _(_.PLUGIN_EXCEPTION, addon=ADDON_NAME, version=ADDON_VERSION)

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
def progress(message='', heading=None, percent=0, background=False):
    dialog = Progress(message=message, heading=heading, percent=percent, background=background)

    try:
        yield dialog
    finally:
        dialog.close()

def notification(message, heading=None, icon=None, time=3000, sound=False):
    heading = _make_heading(heading)
    icon    = ADDON_ICON if not icon else icon

    xbmcgui.Dialog().notification(heading, message, icon, time, sound)

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
            resume_from=None, force_resume=False):

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

    def get_url_headers(self):
        headers = {}
        for key in self.headers:
            headers[key.lower()] = self.headers[key]

        if 'connection-timeout' not in headers:
            headers['connection-timeout'] = settings.getInt('http_timeout', 30)

        if 'verifypeer' not in headers and not settings.getBool('verify_ssl', True):
            headers['verifypeer'] = 'false'

        string = ''
        for key in self.headers:
            string += u'{0}={1}&'.format(key, quote(u'{}'.format(self.headers[key]).encode('utf8')))

        if self.cookies:
            string += 'Cookie='
            for key in self.cookies:
                string += u'{0}%3D{1}; '.format(key, quote(u'{}'.format(self.cookies[key]).encode('utf8')))

        return string.strip('&')

    def get_li(self):
        proxy_path = settings.common_settings.get('_proxy_path')

        if KODI_VERSION < 18:
            li = xbmcgui.ListItem()
        else:
            li = xbmcgui.ListItem(offscreen=True)

        if self.label:
            li.setLabel(self.label)
            if not (self.info.get('plot') or '').strip():
                self.info['plot'] = self.label

            if not self.info.get('title'):
                self.info['title'] = self.label

        if self.info:
            if self.info.get('mediatype') in ('tvshow','season') and settings.getBool('show_series_folders', True):
                self.info.pop('mediatype')

            if self.info.get('mediatype') == 'movie':
                self.info.pop('season', None)
                self.info.pop('episode', None)
                self.info.pop('tvshowtitle', None)

            li.setInfo('video', self.info)

        if self.specialsort:
            li.setProperty('specialsort', self.specialsort)

        if self.video:
            li.addStreamInfo('video', self.video)

        if self.audio:
            li.addStreamInfo('audio', self.audio)

        if self.art:
            defaults = {
                'poster':    'thumb',
                'landscape': 'thumb',
                'icon':      'thumb',
            }

            for key in defaults:
                if key not in self.art:
                    self.art[key] = self.art.get(defaults[key])

            for key in self.art:
                if self.art[key] and self.art[key].lower().startswith('http'):
                    self.art[key] = self.art[key].replace(' ', '%20')
                elif self.art[key] and self.art[key].lower().startswith('plugin'):
                    self.art[key] = proxy_path + self.art[key]

            li.setArt(self.art)

        if self.playable:
            li.setProperty('IsPlayable', 'true')
            if self.path:
                self.path = add_url_args(self.path, _play=1)

        if self.context:
            li.addContextMenuItems(self.context)

        if self.resume_from is not None:
            self.properties['ResumeTime'] = self.resume_from
            self.properties['TotalTime'] = self.resume_from

        if not self.force_resume and len(sys.argv) > 3 and sys.argv[3].lower() == 'resume:true':
            self.properties.pop('ResumeTime', None)
            self.properties.pop('TotalTime', None)

        for key in self.properties:
            li.setProperty(key, u'{}'.format(self.properties[key]))

        headers = self.get_url_headers()
        mimetype = self.mimetype

        def get_url(url):
            _url = url.lower()

            if _url.startswith('plugin://') or (_url.startswith('http') and self.use_proxy and not _url.startswith(proxy_path)) and settings.common_settings.getBool('proxy_enabled', True):
                url = u'{}{}'.format(proxy_path, url)

            return url

        license_url = None
        if self.inputstream and self.inputstream.check():
            if KODI_VERSION < 19:
                li.setProperty('inputstreamaddon', self.inputstream.addon_id)
            else:
                li.setProperty('inputstream', self.inputstream.addon_id)

            li.setProperty('{}.manifest_type'.format(self.inputstream.addon_id), self.inputstream.manifest_type)

            if self.inputstream.license_type:
                li.setProperty('{}.license_type'.format(self.inputstream.addon_id), self.inputstream.license_type)

            if headers:
                li.setProperty('{}.stream_headers'.format(self.inputstream.addon_id), headers)

            if self.inputstream.license_key:
                license_url = self.inputstream.license_key
                li.setProperty('{}.license_key'.format(self.inputstream.addon_id), u'{url}|Content-Type={content_type}&{headers}|{challenge}|{response}'.format(
                    url = get_url(self.inputstream.license_key),
                    headers = headers,
                    content_type = self.inputstream.content_type,
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

            if self.inputstream.mimetype and not mimetype:
                mimetype = self.inputstream.mimetype

            for key in self.inputstream.properties:
                li.setProperty(self.inputstream.addon_id+'.'+key, self.inputstream.properties[key])
        else:
            self.inputstream = None

        def make_sub(url, language='unk', mimetype='', forced=False):
            if not url.lower().startswith('http') and not url.lower().startswith('plugin://'):
                return url

            ## using dash, we can embed subs
            if self.inputstream and self.inputstream.manifest_type == 'mpd':
                if mimetype not in ('application/ttml+xml', 'text/vtt') and not url.lower().startswith('plugin://'):
                    ## can't play directly - covert to webvtt
                    proxy_data['middleware'][url] = {'type': MIDDLEWARE_CONVERT_SUB}
                    mimetype = 'text/vtt'

                proxy_data['subtitles'].append([mimetype, language, url, 'forced' if forced else None])
                return None

            ## only srt or webvtt (text/) supported
            if not mimetype.startswith('text/') and not url.lower().startswith('plugin://'):
                proxy_data['middleware'][url] = {'type': MIDDLEWARE_CONVERT_SUB}
                mimetype = 'text/vtt'

            proxy_url = '{}{}.srt'.format(language, '.forced' if forced else '')
            proxy_data['path_subs'][proxy_url] = url

            return u'{}{}'.format(proxy_path, proxy_url)

        if self.path and (self.path.lower().startswith('http://') or self.path.lower().startswith('https://')):
            if not mimetype:
                parse = urlparse(self.path.lower())
                if parse.path.endswith('.m3u') or parse.path.endswith('.m3u8'):
                    mimetype = 'application/vnd.apple.mpegurl'
                elif parse.path.endswith('.mpd'):
                    mimetype = 'application/dash+xml'
                elif parse.path.endswith('.ism'):
                    mimetype = 'application/vnd.ms-sstr+xml'

            self.path = url_sub(self.path)
            self.path = fix_url(self.path)

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
                'verify_ssl': settings.getBool('verify_ssl', True),
                'subtitles': [],
                'path_subs': {},
                'addon_id': ADDON_ID,
                'quality': QUALITY_DISABLED,
                'middleware': {},
                'type': None,
                'dns_rewrites': get_dns_rewrites(),
            }

            if mimetype == 'application/vnd.apple.mpegurl':
                proxy_data['type'] = 'm3u8'
            elif mimetype == 'application/dash+xml':
                proxy_data['type'] = 'mpd'

            proxy_data.update(self.proxy_data)

            for key in ['default_language', 'default_subtitle']:
                value = settings.get(key, '')
                if value:
                    proxy_data[key] = value

            if self.subtitles:
                subs = []
                for sub in self.subtitles:
                    if type(sub) == list:
                        sub = make_sub(*sub)
                    else:
                        sub = make_sub(**sub)
                    if sub:
                        subs.append(sub)

                li.setSubtitles(list(subs))

            set_kodi_string('_slyguy_quality', json.dumps(proxy_data))

            self.path = get_url(self.path)
            if headers and '|' not in self.path:
                self.path = u'{}|{}'.format(self.path, headers)

        if mimetype:
            li.setMimeType(mimetype)
            li.setContentLookup(False)

        if self.path:
            li.setPath(self.path)

        return li

    def play(self):
        li = self.get_li()
        xbmc.Player().play(self.path, li)