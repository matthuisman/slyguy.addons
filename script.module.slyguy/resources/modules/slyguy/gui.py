import sys
import json
import time

from six.moves.urllib_parse import urlparse
from kodi_six import xbmcgui, xbmc

from slyguy import settings, _
from slyguy.constants import *
from slyguy.router import add_url_args
from slyguy.smart_urls import get_dns_rewrites
from slyguy.util import fix_url, set_kodi_string, hash_6, get_url_headers, get_headers_from_url
from slyguy.session import Session
from slyguy.dialog import * #backwards compatb


if KODI_VERSION >= 20:
    from .listitem import ListItemInfoTag


def redirect(location):
    xbmc.executebuiltin('Container.Update({},replace)'.format(location))


def get_view_id():
    return xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()


def refresh():
    set_kodi_string('slyguy_refresh', '1')
    xbmc.executebuiltin('Container.Refresh')


def get_art_url(url, headers=None):
    if not url or not url.lower().startswith(('http', 'plugin')):
        return url

    if url.lower().startswith('http'):
        url = url.replace(' ', '%20')

    _headers = {'user-agent': DEFAULT_USERAGENT}
    _headers.update(headers or {})
    _headers.update(get_headers_from_url(url))

    if settings.getBool('proxy_enabled', True):
        proxy_path = settings.get('_proxy_path')
        if proxy_path:
            _headers.update({'session_type': 'art', 'session_addonid': ADDON_ID})
            if not url.lower().startswith(proxy_path.lower()):
                url = proxy_path + url

    return url.split('|')[0] + '|' + get_url_headers(_headers)


def notification(message, heading=None, icon=None, time=3000, sound=False):
    heading = make_heading(heading)
    icon = ADDON_ICON if not icon else icon
    xbmcgui.Dialog().notification(heading, message, get_art_url(icon), time, sound)


def select(heading=None, options=None, autoclose=None, multi=False, **kwargs):
    heading = make_heading(heading)
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


class Item(object):
    def __init__(self, id=None, label='', path=None, playable=False, info=None, context=None,
            headers=None, cookies=None, properties=None, is_folder=None, art=None, inputstream=None,
            video=None, audio=None, subtitles=None, use_proxy=True, specialsort=None, custom=None, proxy_data=None,
            resume_from=None, force_resume=False, dns_rewrites=None, slug=None, hide_favourites=None, no_resume=None):

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
        self.hide_favourites = hide_favourites
        self.slug = slug
        self.no_resume = no_resume
        if self.slug is None:
            try:
                self.slug = sys.argv[2]
            except IndexError:
                self.slug = self.path

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
        proxy_path = settings.get('_proxy_path')

        if KODI_VERSION < 18:
            li = xbmcgui.ListItem()
        else:
            li = xbmcgui.ListItem(offscreen=True)

        info = self.info.copy()
        if self.label:
            li.setLabel(self.label)

        if self.no_resume:
            self.resume_from = 0
            info['duration'] = 0
            info['playcount'] = -2 # disable mark as watched

        if not self.playable and 'playcount' not in info:
            info['playcount'] = -2 # disable mark as watched

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

            if info or self.is_folder:
                #TODO: do own 20+ wrapper layer
                ListItemInfoTag(li, 'video').set_info(info)
        else:
            if info.get('date'):
                try: info['date'] = '{}.{}.{}'.format(info['date'][8:10], info['date'][5:7], info['date'][0:4])
                except: pass

            if info.get('cast'):
                try: info['cast'] = [(member['name'], member['role']) for member in info['cast']]
                except: pass

            if info or self.is_folder:
                li.setInfo('video', info)

        if self.video:
            li.addStreamInfo('video', self.video)
        if self.audio:
            li.addStreamInfo('audio', self.audio)

        if self.art:
            defaults = {
                'poster': 'thumb',
                'landscape': 'thumb',
                'icon': 'thumb',
                'banner': 'clearlogo',
            }

            art = {}
            for key in self.art:
                art[key] = get_art_url(self.art[key])

            for key in defaults:
                if key not in art:
                    art[key] = art.get(defaults[key])

            li.setArt(art)

        if self.specialsort:
            self.properties['specialsort'] = self.specialsort

        if self.hide_favourites and KODI_VERSION > 20:
            # Kodi 21+ only
            self.properties['hide_add_remove_favourite'] = 'true'

        context_items = [x for x in self.context]
        if not playing:
            if self.playable:
                self.properties['IsPlayable'] = 'true'
                if self.path:
                    self.path = add_url_args(self.path, _play=1)
                if KODI_VERSION < 20 or ROUTE_LIVE_TAG not in self.path:
                    # PlayNext added in Kodi 18
                    if KODI_VERSION > 17:
                        context_items.append((_.PLAY_NEXT, 'Action(PlayNext)'))
                    context_items.append((_.QUEUE_ITEM, 'Action(Queue)'))
            else:
                self.properties['IsPlayable'] = 'false'

        if context_items:
            li.addContextMenuItems(context_items)

        if self.resume_from is not None:
            # Setting this on Kodi 18 or below removes all list item data (fixed in 19)
            self.properties['ResumeTime'] = self.resume_from
            self.properties['TotalTime'] = 1

        if not self.force_resume and len(sys.argv) > 3 and sys.argv[3].lower() == 'resume:true':
            self.properties.pop('ResumeTime', None)
            self.properties.pop('TotalTime', None)

        if KODI_VERSION >= 20 and 'ResumeTime' in self.properties:
            li.getVideoInfoTag().setResumePoint(
                self.properties.pop('ResumeTime'),
                self.properties.pop('TotalTime', 1)
            )

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

        def get_url(url, plugin_proxy=False):
            _url = url.lower()

            if os.path.exists(xbmc.translatePath(url)) or _url.startswith('special://') or (plugin_proxy and _url.startswith('plugin://')) or (is_http(_url) and self.use_proxy and not _url.startswith(proxy_path)) and settings.getBool('proxy_enabled', True):
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

            if KODI_VERSION > 19:
                li.setProperty('{}.chooser_resolution_max'.format(self.inputstream.addon_id), '4K')
                li.setProperty('{}.chooser_resolution_secure_max'.format(self.inputstream.addon_id), '4K')
                if self.inputstream.manifest_type == 'hls' and KODI_VERSION > 20:
                    # dash sets its own delay in proxy
                    li.setProperty('inputstream.adaptive.live_delay', '24')

            if self.inputstream.license_key:
                license_url = self.inputstream.license_key
                license_headers = get_url_headers(self.inputstream.license_headers) if self.inputstream.license_headers else headers
                li.setProperty('{}.license_key'.format(self.inputstream.addon_id), u'{url}|Content-Type={content_type}{headers}|{challenge}|{response}'.format(
                    url = get_url(redirect_url(fix_url(self.inputstream.license_key)), plugin_proxy=True),
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
                    'slug': '{}-{}'.format(ADDON_ID, self.slug),
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
                    'quality': QUALITY_SKIP,
                    'middleware': {},
                    'type': None,
                    'skip_next_channel': settings.getBool('skip_next_channel', False),
                    'h265': settings.getBool('h265', False),
                    'vp9': settings.getBool('vp9', False),
                    'av1': settings.getBool('av1', False),
                    'hdr10': settings.getBool('hdr10', False),
                    'dolby_vision': settings.getBool('dolby_vision', False),
                    'dolby_atmos': settings.getBool('dolby_atmos', False),
                    'ac3': settings.getBool('ac3', False),
                    'ec3': settings.getBool('ec3', False),
                    'verify': settings.getBool('verify_ssl', True),
                    'timeout': settings.getInt('http_timeout', 30),
                    'dns_rewrites': get_dns_rewrites(self.dns_rewrites),
                    'proxy_server': settings.get('proxy_server') or settings.get('proxy_server'),
                    'ip_mode': settings.IP_MODE.value,
                    'max_bandwidth': settings.getInt('max_bandwidth', 0),
                    'max_width': settings.getInt('max_width', 0),
                    'max_height': settings.getInt('max_width', 0),
                    'max_channels': settings.getInt('max_channels', 0),
                }

                if mimetype == 'application/vnd.apple.mpegurl':
                    proxy_data['type'] = 'm3u8'
                elif mimetype == 'application/dash+xml':
                    proxy_data['type'] = 'mpd'

                if settings.getBool('ignore_display_resolution', False) is False:
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
