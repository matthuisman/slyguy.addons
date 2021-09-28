import threading
import os
import re
import time
import json
import shutil

from xml.dom.minidom import parseString
from functools import cmp_to_key

import arrow
from requests import ConnectionError
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver import ThreadingMixIn
from six.moves.urllib.parse import urlparse, urljoin, unquote_plus, parse_qsl
from kodi_six import xbmc
from pycaption import detect_format, WebVTTWriter

from slyguy import settings, gui, inputstream
from slyguy.log import log
from slyguy.constants import *
from slyguy.util import check_port, remove_file, get_kodi_string, set_kodi_string, fix_url, run_plugin
from slyguy.plugin import failed_playback
from slyguy.exceptions import Exit
from slyguy.session import RawSession
from slyguy.router import add_url_args

from .language import _

REMOVE_IN_HEADERS = ['upgrade', 'host', 'accept-encoding']
REMOVE_OUT_HEADERS = ['date', 'server', 'transfer-encoding', 'keep-alive', 'connection']

DEFAULT_PORT = 52103
HOST = '127.0.0.1'

PORT = check_port(DEFAULT_PORT)
if not PORT:
    PORT = check_port()

PROXY_PATH = 'http://{}:{}/'.format(HOST, PORT)
settings.set('_proxy_path', PROXY_PATH)

CODECS = [
    ['avc', 'H.264'],
    ['hvc', 'H.265'],
    ['hev', 'H.265'],
    ['mp4v', 'MPEG-4'],
    ['mp4s', 'MPEG-4'],
    ['dvh', 'H.265 Dolby Vision'],
]

CODEC_RANKING = ['MPEG-4', 'H.264', 'H.265', 'HDR', 'H.265 Dolby Vision']

PROXY_GLOBAL = {
    'last_qualities': [],
    'session': {},
}

def _lang_allowed(lang, lang_list):
    for _lang in lang_list:
        if not _lang:
            continue

        if lang.startswith(_lang):
            return True

    return False

def middleware_regex(response, pattern, **kwargs):
    data = response.stream.content.decode('utf8')
    match = re.search(pattern, data)
    if match:
        response.stream.content = match.group(1).encode('utf8')

def middleware_convert_sub(response, **kwargs):
    data = response.stream.content.decode('utf8')
    reader = detect_format(data)
    if reader:
        data = WebVTTWriter().write(reader().read(data))
        response.stream.content = data.encode('utf8')
        response.headers['content-type'] = 'text/vtt'

def middleware_plugin(response, url, **kwargs):
    path = 'special://temp/proxy.middleware'
    real_path = xbmc.translatePath(path)
    with open(real_path, 'wb') as f:
        f.write(response.stream.content)

    if ADDON_DEV:
        shutil.copy(real_path, real_path+'.in')

    url = add_url_args(url, _path=path)
    dirs, files = run_plugin(url, wait=True)
    if not files:
        raise Exception('No data returned from plugin')

    data = json.loads(unquote_plus(files[0]))
    with open(real_path, 'rb') as f:
        response.stream.content = f.read()

    response.headers.update(data.get('headers', {}))
    if ADDON_DEV:
        shutil.copy(real_path, real_path+'.out')

    remove_file(real_path)

middlewares = {
    MIDDLEWARE_CONVERT_SUB: middleware_convert_sub,
    MIDDLEWARE_REGEX: middleware_regex,
    MIDDLEWARE_PLUGIN: middleware_plugin,
}

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        try:
            BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except (IOError, OSError) as e:
            pass

    def log_message(self, format, *args):
        return

    def setup(self):
        BaseHTTPRequestHandler.setup(self)
        self.request.settimeout(5)

    def _get_url(self, method):
        url = self.path.lstrip('/').strip('\\')
        log.debug('{} IN: {}'.format(method, url))

        self._headers = {}
        for header in self.headers:
            if header.lower() not in REMOVE_IN_HEADERS:
                self._headers[header.lower()] = self.headers[header]

        length = int(self._headers.get('content-length', 0))
        self._post_data = self.rfile.read(length) if length else None

        self._session = PROXY_GLOBAL['session']

        try:
            proxy_data = json.loads(get_kodi_string('_slyguy_quality'))
            if self._session.get('session_id') != proxy_data['session_id']:
                self._session = {}

            self._session.update(proxy_data)
            set_kodi_string('_slyguy_quality', '')
        except:
            pass

        PROXY_GLOBAL['session'] = self._session

        url = self._session.get('path_subs', {}).get(url) or url

        if url.lower().startswith('plugin'):
            url = self._update_urls(url, self._plugin_request(url))

        return url

    def _update_urls(self, url, new_url):
        if url == new_url:
            return new_url

        if url == self._session.get('manifest'):
            self._session['manifest'] = new_url
        if url == self._session.get('license_url'):
            self._session['license_url'] = new_url
        if url in self._session.get('middleware', {}):
            self._session['middleware'][new_url] = self._session['middleware'].pop(url)

        return new_url

    def _plugin_request(self, url):
        log.debug('PLUGIN REQUEST: {}'.format(url))
        dirs, files = run_plugin(url, wait=True)
        if not files:
            raise Exception('No data returned from plugin')

        data = json.loads(unquote_plus(files[0]))
        self._headers.update(data.get('headers', {}))
        return data['url']

    def _middleware(self, url, response):
        if url not in self._session.get('middleware', {}):
            return

        middleware = self._session['middleware'][url].copy()

        _type = middleware.pop('type')
        if _type not in middlewares:
            return

        log.debug('MIDDLEWARE: {}'.format(_type))
        return middlewares[_type](response, **middleware)

    def do_GET(self):
        url = self._get_url('GET')
        response = self._proxy_request('GET', url)

        if self._session.get('redirecting') or not self._session.get('type') or not self._session.get('manifest') or int(response.headers.get('content-length', 0)) > 1000000:
            self._output_response(response)
            return

        parse = urlparse(self.path.lower())

        try:
            if self._session.get('type') == 'm3u8' and (url == self._session['manifest'] or parse.path.endswith('.m3u') or parse.path.endswith('.m3u8')):
                self._parse_m3u8(response)

            elif self._session.get('type') == 'mpd' and url == self._session['manifest']:
                self._parse_dash(response)
                self._session['manifest'] = None  # unset manifest url so isn't parsed again
        except Exception as e:
            log.exception(e)

            if type(e) != Exit and url == self._session['manifest']:
                gui.error(_.QUALITY_PARSE_ERROR)

            response.status_code = 500
            response.stream.content = str(e).encode('utf-8')
            failed_playback()

        self._output_response(response)

    def _quality_select(self, qualities):
        def codec_rank(_codecs):
            highest = -1

            for codec in _codecs:
                for _codec in CODECS:
                    if codec.lower().startswith(_codec[0].lower()) and _codec[1] in CODEC_RANKING:
                        rank = CODEC_RANKING.index(_codec[1])
                        if not highest or rank > highest:
                            highest = rank

            return highest

        def compare(a, b):
            if a['resolution'] and b['resolution']:
                if int(a['resolution'].split('x')[0]) > int(b['resolution'].split('x')[0]):
                    return 1
                elif int(a['resolution'].split('x')[0]) < int(b['resolution'].split('x')[0]):
                    return -1

            # Same resolution - compare codecs
            a_rank = codec_rank(a['codecs'])
            b_rank = codec_rank(b['codecs'])

            if a_rank > b_rank:
                return 1
            elif a_rank < b_rank:
                return -1

            # Same codec rank - compare bandwidth
            if a['bandwidth'] and b['bandwidth']:
                if a['bandwidth'] > b['bandwidth']:
                    return 1
                elif a['bandwidth'] < b['bandwidth']:
                    return -1

            # Same bandwidth - they are equal (could compare framerate)
            return 0

        def _stream_label(stream):
            try: fps = _(_.QUALITY_FPS, fps=float(stream['frame_rate']))
            except: fps = ''

            codec_string = ''
            for codec in stream['codecs']:
                for _codec in CODECS:
                    if codec.lower().startswith(_codec[0].lower()):
                        codec_string += ' ' + _codec[1]

            return _(_.QUALITY_BITRATE, bandwidth=int((stream['bandwidth']/10000.0))/100.00, resolution=stream['resolution'], fps=fps, codecs=codec_string.strip()).replace('  ', ' ')

        if self._session.get('selected_quality') is not None:
            if self._session['selected_quality'] in (QUALITY_DISABLED, QUALITY_SKIP):
                return None
            else:
                return qualities[self._session['selected_quality']]

        quality_compare = cmp_to_key(compare)

        quality = int(self._session.get('quality', QUALITY_ASK))
        streams = sorted(qualities, key=quality_compare, reverse=True)

        if not streams:
            quality = QUALITY_DISABLED
        elif len(streams) < 2:
            quality = QUALITY_BEST

        if quality == QUALITY_ASK:
            options = []
            options.append([QUALITY_BEST, _.QUALITY_BEST])

            for x in streams:
                options.append([x, _stream_label(x)])

            options.append([QUALITY_LOWEST, _.QUALITY_LOWEST])
            options.append([QUALITY_SKIP, _.QUALITY_SKIP])

            values = [x[0] for x in options]
            labels = [x[1] for x in options]

            default = 0
            remove = None
            for quality in PROXY_GLOBAL['last_qualities']:
                if quality[0] == self._session['slug']:
                    remove = quality
                    default = quality[1]
                    break

            index = gui.select(_.PLAYBACK_QUALITY, labels, preselect=default, autoclose=5000)
            if index < 0:
                raise Exit('Cancelled quality select')

            quality = values[index]

            if remove:
                PROXY_GLOBAL['last_qualities'].remove(remove)

            if index != default:
                PROXY_GLOBAL['last_qualities'].insert(0, [self._session['slug'], index])
                PROXY_GLOBAL['last_qualities'] = PROXY_GLOBAL['last_qualities'][:MAX_QUALITY_HISTORY]

        if quality in (QUALITY_DISABLED, QUALITY_SKIP):
            quality = quality
        elif quality == QUALITY_BEST:
            quality = streams[0]
        elif quality == QUALITY_LOWEST:
            quality = streams[-1]
        elif quality not in streams:
            options = [streams[-1]]
            for stream in streams:
                if quality >= stream['bandwidth']:
                    options.append(stream)
            quality = sorted(options, key=quality_compare, reverse=True)[0]

        if quality in qualities:
            self._session['selected_quality'] = qualities.index(quality)
            return qualities[self._session['selected_quality']]
        else:
            self._session['selected_quality'] = quality
            return None

    def _parse_dash(self, response):
        if ADDON_DEV:
            root = parseString(response.stream.content)
            mpd = root.toprettyxml(encoding='utf-8')
            mpd = b"\n".join([ll.rstrip() for ll in mpd.splitlines() if ll.strip()])
            with open(xbmc.translatePath('special://temp/in.mpd'), 'wb') as f:
                f.write(mpd)

            start = time.time()

        data = response.stream.content.decode('utf8')

        ## SUPPORT NEW DOLBY FORMAT https://github.com/xbmc/inputstream.adaptive/pull/466
        data = data.replace('tag:dolby.com,2014:dash:audio_channel_configuration:2011', 'urn:dolby:dash:audio_channel_configuration:2011')
        ## SUPPORT EC-3 CHANNEL COUNT https://github.com/xbmc/inputstream.adaptive/pull/618
        data = data.replace('urn:mpeg:mpegB:cicp:ChannelConfiguration', 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011')

        root = parseString(data.encode('utf8'))
        mpd = root.getElementsByTagName("MPD")[0]

        mpd_attribs = list(mpd.attributes.keys())

        ## Remove publishTime PR: https://github.com/xbmc/inputstream.adaptive/pull/564
        if 'publishTime' in mpd_attribs:
            mpd.removeAttribute('publishTime')
            log.debug('Dash Fix: publishTime removed')

        ## Remove mediaPresentationDuration from live PR: https://github.com/xbmc/inputstream.adaptive/pull/762
        if (mpd.getAttribute('type') == 'dynamic' or 'timeShiftBufferDepth' in mpd_attribs) and 'mediaPresentationDuration' in mpd_attribs:
            mpd.removeAttribute('mediaPresentationDuration')
            log.debug('Dash Fix: mediaPresentationDuration removed from live')

        ## Fix mpd overalseconds bug issue: https://github.com/xbmc/inputstream.adaptive/issues/731
        if mpd.getAttribute('type') == 'dynamic' and 'timeShiftBufferDepth' not in mpd_attribs:
            if 'availabilityStartTime' in mpd_attribs:
                buffer_seconds = (arrow.now() - arrow.get(mpd.getAttribute('availabilityStartTime'))).total_seconds()
            else:
                buffer_seconds = 60

            mpd.setAttribute('timeShiftBufferDepth', 'PT{}S'.format(buffer_seconds))
            log.debug('Dash Fix: {}S timeShiftBufferDepth added'.format(buffer_seconds))

        ## SORT ADAPTION SETS BY BITRATE ##
        video_sets = []
        audio_sets = []
        lang_adap_sets = []
        streams, all_streams = [], []
        adap_parent = None

        default_language = self._session.get('default_language', '')
        original_language = self._session.get('original_language', '')
        audio_description = self._session.get('audio_description', True)
        subs_whitelist = [x.strip().lower() for x in self._session.get('subs_whitelist', '').split(',') if x]

        for period_index, period in enumerate(root.getElementsByTagName('Period')):
            rep_index = 0
            for adap_set in period.getElementsByTagName('AdaptationSet'):
                adap_parent = adap_set.parentNode

                highest_bandwidth = 0
                is_video = False
                is_trick = False

                for stream in adap_set.getElementsByTagName("Representation"):
                    attribs = {}

                    ## Make sure Representation are last in adaptionset
                    adap_set.removeChild(stream)
                    adap_set.appendChild(stream)
                    #######

                    for key in adap_set.attributes.keys():
                        attribs[key] = adap_set.getAttribute(key)

                    for key in stream.attributes.keys():
                        attribs[key] = stream.getAttribute(key)

                    bandwidth = 0
                    if 'bandwidth' in attribs:
                        bandwidth = int(attribs['bandwidth'])

                    if 'maxPlayoutRate' in attribs:
                        is_trick = True

                    if 'audio' in attribs.get('mimeType', ''):
                        if default_language and attribs.get('lang').lower().split('-')[0] == default_language.lower().split('-')[0]:
                            adap_set.setAttribute('default', 'true')

                        if original_language and attribs.get('lang').lower().split('-')[0] == original_language.lower().split('-')[0]:
                            adap_set.setAttribute('original', 'true')

                        is_atmos = False
                        atmos_channels = None
                        for supelem in stream.getElementsByTagName('SupplementalProperty'):
                            if supelem.getAttribute('value') == 'JOC':
                                is_atmos = True
                            if 'EC3_ExtensionComplexityIndex' in (supelem.getAttribute('schemeIdUri') or ''):
                                atmos_channels = supelem.getAttribute('value')

                        if is_atmos:
                            adap_set.removeChild(stream)
                            new_set = adap_set.cloneNode(deep=True)

                            new_set.setAttribute('id', '{}-atmos'.format(attribs.get('id','')))
                            new_set.setAttribute('lang', _(_.ATMOS, name=attribs.get('lang','')))

                            for elem in new_set.getElementsByTagName("Representation"):
                                new_set.removeChild(elem)
                            new_set.appendChild(stream)

                            if atmos_channels:
                                for elem in stream.getElementsByTagName("AudioChannelConfiguration"):
                                    stream.removeChild(elem)

                                elem = root.createElement('AudioChannelConfiguration')
                                elem.setAttribute('schemeIdUri', 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011')
                                elem.setAttribute('value', atmos_channels)
                                stream.appendChild(elem)

                            audio_sets.append([bandwidth, new_set, adap_parent])
                            if adap_set in lang_adap_sets:
                                lang_adap_sets.append(new_set)
                            log.debug('Dash Fix: Atmos representation moved to own adaption set')
                            continue

                    if bandwidth > highest_bandwidth:
                        highest_bandwidth = bandwidth

                    if 'video' in attribs.get('mimeType', '') and not is_trick:
                        is_video = True

                        resolution = ''
                        if 'width' in attribs and 'height' in attribs:
                            resolution = '{}x{}'.format(attribs['width'], attribs['height'])

                        frame_rate = ''
                        if 'frameRate'in attribs:
                            frame_rate = attribs['frameRate']
                            try:
                                if '/' in str(frame_rate):
                                    split = frame_rate.split('/')
                                    frame_rate = float(split[0]) / float(split[1])
                            except:
                                frame_rate = ''

                        codecs = [x for x in attribs.get('codecs', '').split(',') if x]
                        stream = {'bandwidth': bandwidth, 'resolution': resolution, 'frame_rate': frame_rate, 'codecs': codecs, 'rep_index': rep_index, 'elem': stream}
                        all_streams.append(stream)
                        rep_index += 1

                        if period_index == 0:
                            streams.append(stream)

                adap_parent.removeChild(adap_set)

                if is_trick:
                    continue

                if is_video:
                    video_sets.append([highest_bandwidth, adap_set, adap_parent])
                else:
                    audio_sets.append([highest_bandwidth, adap_set, adap_parent])

        video_sets.sort(key=lambda  x: x[0], reverse=True)
        audio_sets.sort(key=lambda  x: x[0], reverse=True)

        for elem in video_sets:
            elem[2].appendChild(elem[1])

        for elem in audio_sets:
            elem[2].appendChild(elem[1])

        ## Insert subtitles
        if adap_parent:
            for idx, subtitle in enumerate(self._session.get('subtitles') or []):
                elem = root.createElement('AdaptationSet')
                elem.setAttribute('contentType', 'text')
                elem.setAttribute('mimeType', subtitle[0])
                elem.setAttribute('lang', subtitle[1])
                elem.setAttribute('id', 'caption_{}'.format(idx))
                #elem.setAttribute('original', 'true')
                #elem.setAttribute('default', 'true')
                #elem.setAttribute('impaired', 'true')

                if subtitle[3] == 'forced':
                    elem.setAttribute('forced', 'true')

                elem2 = root.createElement('Representation')
                elem2.setAttribute('id', 'caption_rep_{}'.format(idx))

                if 'ttml' in subtitle[0]:
                    elem2.setAttribute('codecs', 'ttml')

                elem3 = root.createElement('BaseURL')
                elem4 = root.createTextNode(subtitle[2])

                elem3.appendChild(elem4)
                elem2.appendChild(elem3)
                elem.appendChild(elem2)

                adap_parent.appendChild(elem)
        ##################

        ## REMOVE SUBS
        if subs_whitelist:
            for adap_set in root.getElementsByTagName('AdaptationSet'):
                if adap_set.getAttribute('contentType') == 'text':
                    language = adap_set.getAttribute('lang')
                    if not _lang_allowed(language.lower().strip(), subs_whitelist):
                        adap_set.parentNode.removeChild(adap_set)
                        log.debug('Removed subtitle adapt set: {}'.format(adap_set.getAttribute('id')))
        ################

        ## Remove audio_description
        if not audio_description:
            for row in audio_sets:
                for elem in row[1].getElementsByTagName('Accessibility'):
                    if elem.getAttribute('schemeIdUri') == 'urn:tva:metadata:cs:AudioPurposeCS:2007':
                        row[2].removeChild(row[1])
                        log.debug('Removed audio description adapt set: {}'.format(row[1].getAttribute('id')))
                        break
        ############

        ## Convert BaseURLS
        base_url_parents = []
        for elem in root.getElementsByTagName('BaseURL'):
            url = elem.firstChild.nodeValue

            if elem.parentNode in base_url_parents:
                log.debug('Non-1st BaseURL removed: {}'.format(url))
                elem.parentNode.removeChild(elem)
                continue

            if url.startswith('/'):
                url = urljoin(response.url, url)

            if '://' in url:
                elem.firstChild.nodeValue = PROXY_PATH + url

            base_url_parents.append(elem.parentNode)
        ################

        ## Convert to proxy paths
        elems = root.getElementsByTagName('SegmentTemplate')
        elems.extend(root.getElementsByTagName('SegmentURL'))

        def get_parent_node(node, tag_name, levels=99):
            if not node.parentNode or levels == 0:
                return None

            siblings = [x for x in node.parentNode.childNodes if x != node and x.nodeType == x.ELEMENT_NODE and x.tagName == tag_name]
            if siblings:
                return siblings[0]
            else:
                return get_parent_node(node.parentNode, tag_name, levels-1)

        for e in elems:
            def process_attrib(attrib):
                if attrib not in e.attributes.keys():
                    return

                url = e.getAttribute(attrib)
                if '://' in url:
                    e.setAttribute(attrib, PROXY_PATH + url)
                else:
                    ## Fixed with https://github.com/xbmc/inputstream.adaptive/pull/606
                    base_url = get_parent_node(e, 'BaseURL')
                    if base_url and not base_url.firstChild.nodeValue.endswith('/'):
                        base_url.firstChild.nodeValue = base_url.firstChild.nodeValue + '/'
                        log.debug('Dash Fix: base_url / fixed')

                    # Fixed with https://github.com/xbmc/inputstream.adaptive/pull/668
                    parent_template = get_parent_node(e, 'SegmentTemplate', levels=2)
                    if parent_template:
                        for key in parent_template.attributes.keys():
                            if key not in e.attributes.keys():
                                e.setAttribute(key, parent_template.getAttribute(key))

                        parent_template.parentNode.removeChild(parent_template)
                        log.debug('Dash Fix: Double SegmentTemplate removed')

            process_attrib('initialization')
            process_attrib('media')

            ## Remove presentationTimeOffset PR: https://github.com/xbmc/inputstream.adaptive/pull/564/
            if 'presentationTimeOffset' in e.attributes.keys():
                e.removeAttribute('presentationTimeOffset')
                log.debug('Dash Fix: presentationTimeOffset removed')
        ###############

        ## Get selected quality
        selected = self._quality_select(streams)
        if selected:
            for stream in all_streams:
                if stream['rep_index'] != selected['rep_index']:
                    stream['elem'].parentNode.removeChild(stream['elem'])
        #################

        ## Remove empty adaption sets
        for adap_set in root.getElementsByTagName('AdaptationSet'):
            if not adap_set.getElementsByTagName('Representation'):
                adap_set.parentNode.removeChild(adap_set)
        #################

        if ADDON_DEV:
            mpd = root.toprettyxml(encoding='utf-8')
            mpd = b"\n".join([ll.rstrip() for ll in mpd.splitlines() if ll.strip()])

            log.debug('Time taken: {}'.format(time.time() - start))
            with open(xbmc.translatePath('special://temp/out.mpd'), 'wb') as f:
                f.write(mpd)
        else:
            mpd = root.toxml(encoding='utf-8')

        response.stream.content = mpd

    def _parse_m3u8_sub(self, m3u8, url):
        lines = []
        segments = []

        for line in m3u8.splitlines():
            if not line.startswith('#'):
                line = line.strip()
                if not line:
                    continue

                segments.append(line.lower())
                if '/beacon?' in line.lower():
                    parse = urlparse(line)
                    params = dict(parse_qsl(parse.query))
                    for key in params:
                        if key.lower() == 'redirect_path':
                            line = params[key]
                            log.debug('M3U8 Fix: Beacon removed')

            lines.append(line)

        # # bad playlist test
        # if ADDON_DEV:
        #     error_every = 5
        #     error_repeat = 2

        #     self._session['count'] = self._session.get('count', 0) + 1
        #     print(self._session['count'])
        #     if self._session['count'] >= error_every:
        #         if self._session['count'] == error_every + error_repeat - 1:
        #             self._session['count'] = 0
        #         segments = segments[:int(len(segments)/2)]

        self._session['m3u8_last_lines'] = self._session.get('m3u8_last_lines', {})
        if url in self._session['m3u8_last_lines'] and self._session['m3u8_last_lines'][url] not in segments:
            raise Exception('Invalid M3U8 refresh. Could not find previous segment in playlist')

        self._session['m3u8_last_lines'][url] = segments[-1]

        return '\n'.join(lines)

    def _parse_m3u8_master(self, m3u8, manifest_url):
        def _process_media(line):
            attribs = {}

            for key, value in re.findall('([\w-]+)="?([^",]*)[",$]?', line):
                attribs[key.upper()] = value.strip()

            return attribs

        audio_whitelist = [x.strip().lower() for x in self._session.get('audio_whitelist', '').split(',') if x]
        subs_whitelist = [x.strip().lower() for x in self._session.get('subs_whitelist', '').split(',') if x]
        subs_forced = self._session.get('subs_forced', True)
        subs_non_forced = self._session.get('subs_non_forced', True)
        audio_description = self._session.get('audio_description', True)
        original_language = self._session.get('original_language', '').lower().strip()
        default_language = self._session.get('default_language', '').lower().strip()
        default_subtitle = self._session.get('default_subtitle', '').lower().strip()

        stream_inf = None
        streams, all_streams, urls, metas = [], [], [], []
        audio = []
        subtitles = []
        video = []
        new_lines = []
        has_default_audio = False
        found_default_language = False
        has_default_subs = False
        found_default_subs = False

        for line in m3u8.splitlines():
            if not line.strip():
                continue

            if line.startswith('#EXT-X-MEDIA'):
                attribs = _process_media(line)
                if not attribs:
                    continue

                lang = attribs.get('LANGUAGE','').lower().strip()
                if attribs.get('TYPE') == 'AUDIO':
                    audio.append(attribs)
                    if attribs.get('DEFAULT') == 'YES':
                        has_default_audio = True

                    if default_language and lang.startswith(default_language):
                        found_default_language = True

                elif attribs.get('TYPE') == 'SUBTITLES':
                    subtitles.append(attribs)
                    if attribs.get('DEFAULT') == 'YES':
                        has_default_subs = True

                    if default_subtitle and lang.startswith(default_subtitle):
                        found_default_subs = True

            elif line.startswith('#EXT-X-STREAM-INF'):
                stream_inf = line

            elif stream_inf and not line.startswith('#'):
                attribs = _process_media(stream_inf)

                codecs = [x for x in attribs.get('CODECS', '').split(',') if x]
                bandwidth = int(attribs.get('BANDWIDTH') or 0)
                resolution = attribs.get('RESOLUTION', '')
                frame_rate = attribs.get('FRAME-RATE', '')

                url = line
                if '://' in url:
                    url = '/'+'/'.join(url.lower().split('://')[1].split('/')[1:])

                stream = {'bandwidth': int(bandwidth), 'resolution': resolution, 'frame_rate': frame_rate, 'codecs': codecs, 'url': url, 'index': len(video)}
                all_streams.append(stream)
                video.append([stream_inf, line])

                if stream['url'] not in urls and stream_inf not in metas:
                    streams.append(stream)
                    urls.append(stream['url'])
                    metas.append(stream_inf)

                stream_inf = None
            else:
                new_lines.append(line)

        want_subs = None
        if not found_default_language:
            if default_language:
                want_subs = default_language
                default_language = None
        else:
            has_default_audio = False

        if not default_language and not has_default_audio:
            default_language = original_language

        if audio_whitelist:
            audio_whitelist.append(original_language)
            audio_whitelist.append(default_language)

        for attribs in audio:
            lang = attribs.get('LANGUAGE','').lower().strip()

            if audio_whitelist and not _lang_allowed(lang, audio_whitelist):
                continue

            if not audio_description and attribs.get('CHARACTERISTICS','').lower() == 'public.accessibility.describes-video':
                continue

            if 'JOC' in attribs.get('CHANNELS', ''):
                attribs['NAME'] = _(_.ATMOS, name=attribs['NAME'])
                attribs['CHANNELS'] = attribs['CHANNELS'].split('/')[0]

            if default_language:
                attribs['DEFAULT'] = 'YES' if lang.startswith(default_language) else 'NO'

            # FIX es-ES > es / fr-FR > fr languages #
            split = attribs.get('LANGUAGE','').split('-')
            if len(split) > 1 and split[1].lower() == split[0].lower():
                attribs['LANGUAGE'] = split[0]
            #############

            new_line = '#EXT-X-MEDIA:' if attribs else ''
            for key in attribs:
                new_line += u'{}="{}",'.format(key, attribs[key])
            new_lines.append(new_line)

        if not found_default_subs:
            default_subtitle = None
        else:
            has_default_subs = False

        if not found_default_subs and not has_default_subs:
            default_subtitle = want_subs

        if subs_whitelist:
            subs_whitelist.append(default_subtitle)

        for attribs in subtitles:
            lang = attribs.get('LANGUAGE','').lower().strip()

            if subs_whitelist and not _lang_allowed(lang, subs_whitelist):
                continue

            if not subs_forced and attribs.get('FORCED','').upper() == 'YES':
                continue

            if not subs_non_forced and attribs.get('FORCED','').upper() != 'YES':
                continue

            if default_subtitle:
                attribs['DEFAULT'] = 'YES' if lang.startswith(default_subtitle) else 'NO'

            # if 'URI' in attribs:
            #     full_url = urljoin(manifest_url, attribs['URI'])
            #     self._session['middleware'][full_url] = {'type': MIDDLEWARE_CONVERT_SUB}
            #     attribs['URI'] = full_url

            new_line = '#EXT-X-MEDIA:' if attribs else ''
            for key in attribs:
                new_line += u'{}="{}",'.format(key, attribs[key])
            new_lines.append(new_line)

        selected = self._quality_select(streams)
        if selected:
            adjust = 0
            for stream in all_streams:
                if stream['url'] != selected['url']:
                    video.pop(stream['index']-adjust)
                    adjust += 1

        for stream in video:
            new_lines.extend(stream)

        return '\n'.join(new_lines)

    def _parse_m3u8(self, response):
        m3u8 = response.stream.content.decode('utf8')

        is_master = False
        if '#EXTM3U' not in m3u8:
            raise Exception('Invalid m3u8')

        if '#EXT-X-STREAM-INF' in m3u8:
            is_master = True
            file_name = 'master'
        else:
            file_name = 'sub'

        if ADDON_DEV:
            start = time.time()
            _m3u8 = m3u8.encode('utf8')
            _m3u8 = b"\n".join([ll.rstrip() for ll in _m3u8.splitlines() if ll.strip()])
            with open(xbmc.translatePath('special://temp/'+file_name+'-in.m3u8'), 'wb') as f:
                f.write(_m3u8)

        if is_master:
            m3u8 = self._parse_m3u8_master(m3u8, response.url)
        else:
            m3u8 = self._parse_m3u8_sub(m3u8, response.url)

        base_url = urljoin(response.url, '/')

        m3u8 = re.sub(r'^/', r'{}'.format(base_url), m3u8, flags=re.I|re.M)
        m3u8 = re.sub(r'URI="/', r'URI="{}'.format(base_url), m3u8, flags=re.I|re.M)

        ## Convert to proxy paths
        m3u8 = re.sub(r'(https?)://', r'{}\1://'.format(PROXY_PATH), m3u8, flags=re.I)

        m3u8 = m3u8.encode('utf8')

        if ADDON_DEV:
            m3u8 = b"\n".join([ll.rstrip() for ll in m3u8.splitlines() if ll.strip()])
            log.debug('Time taken: {}'.format(time.time() - start))
            with open(xbmc.translatePath('special://temp/'+file_name+'-out.m3u8'), 'wb') as f:
                f.write(m3u8)

        response.stream.content = m3u8

    def _proxy_request(self, method, url):
        self._session['redirecting'] = False

        if not url.lower().startswith('http://') and not url.lower().startswith('https://'):
            response = Response()
            response.headers = {}
            response.stream = ResponseStream(response)

            if os.path.exists(url):
                response.ok = True
                response.status_code = 200
                with open(url, 'rb') as f:
                    response.stream.content = f.read()
                if not ADDON_DEV: remove_file(url)
            else:
                response.ok = False
                response.status_code = 500
                response.stream.content = "File not found: {}".format(url).encode('utf-8')

            return response

        debug = self._session.get('debug_all') or self._session.get('debug_{}'.format(method.lower()))
        if self._post_data and debug:
            with open(xbmc.translatePath('special://temp/{}-request.txt').format(method.lower()), 'wb') as f:
                f.write(self._post_data)

        if not self._session.get('session'):
            self._session['session'] = RawSession()
            self._session['session'].set_dns_rewrites(self._session.get('dns_rewrites', []))
        else:
            self._session['session'].headers.clear()
            #self._session['session'].cookies.clear() #lets handle cookies in session

        ## Fix any double // in url
        url = fix_url(url)

        retries = 3
        # some reason we get connection errors every so often when using a session. something to do with the socket
        for i in range(retries):
            try:
                response = self._session['session'].request(method=method, url=url, headers=self._headers, data=self._post_data, allow_redirects=False, verify=self._session.get('verify_ssl', True), stream=True)
            except ConnectionError as e:
                if 'Connection aborted' not in str(e) or i == retries-1:
                    log.exception(e)
                    raise
            except Exception as e:
                log.exception(e)
                raise
            else:
                break

        response.stream = ResponseStream(response)

        log.debug('{} OUT: {} ({})'.format(method.upper(), url, response.status_code))

        headers = {}
        for header in response.headers:
            if header.lower() not in REMOVE_OUT_HEADERS:
                headers[header.lower()] = response.headers[header]

        response.headers = headers

        if debug:
            with open(xbmc.translatePath('special://temp/{}-response.txt').format(method.lower()), 'wb') as f:
                f.write(response.stream.content)

        if 'location' in response.headers:
            if '://' not in response.headers['location']:
                response.headers['location'] = urljoin(url, response.headers['location'])

            self._session['redirecting'] = True
            self._update_urls(url, response.headers['location'])
            response.headers['location'] = PROXY_PATH + response.headers['location']
            response.stream.content = b''

        if 'set-cookie' in response.headers:
            log.debug('set-cookie: {}'.format(response.headers['set-cookie']))
            ## we handle cookies in the requests session
            response.headers.pop('set-cookie')

        self._middleware(url, response)

        return response

    def _output_headers(self, response):
        self.send_response(response.status_code)

        for d in list(response.headers.items()):
            self.send_header(d[0], d[1])

        self.end_headers()

    def _output_response(self, response):
        self._output_headers(response)

        for chunk in response.stream.iter_content():
            try:
                self.wfile.write(chunk)
            except Exception as e:
                break

    def do_HEAD(self):
        url = self._get_url('HEAD')
        response = self._proxy_request('HEAD', url)
        self._output_response(response)

    def do_POST(self):
        url = self._get_url('POST')
        response = self._proxy_request('POST', url)

        if response.status_code in (406,) and url == self._session.get('license_url') and not xbmc.getCondVisibility('System.Platform.Android') and gui.yes_no(_.WV_FAILED):
            thread = threading.Thread(target=inputstream.install_widevine, kwargs={'reinstall': True})
            thread.start()

        self._output_response(response)

class Response(object):
    pass

class ResponseStream(object):
    def __init__(self, response):
        self._response = response
        self._bytes = None

    @property
    def content(self):
        if not self._bytes:
            self.content = self._response.content

        return self._bytes

    @content.setter
    def content(self, _bytes):
        if not type(_bytes) is bytes:
            raise Exception('Only bytes allowed when setting content')

        self._bytes = _bytes
        self._response.headers['content-length'] = str(len(_bytes))
        self._response.headers.pop('content-range', None)
        self._response.headers.pop('content-encoding', None)

    def iter_content(self):
        if self._bytes is not None:
            yield self._bytes
        else:
            while True:
                try:
                    chunk = self._response.raw.read(CHUNK_SIZE)
                except:
                    chunk = None

                if not chunk:
                    break

                yield chunk

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class Proxy(object):
    started = False

    def start(self):
        if self.started:
            return

        self._server = ThreadedHTTPServer((HOST, PORT), RequestHandler)
        self._server.allow_reuse_address = True
        self._httpd_thread = threading.Thread(target=self._server.serve_forever)
        self._httpd_thread.start()
        self.started = True
        log.info("Proxy Started: {}:{}".format(HOST, PORT))

    def stop(self):
        if not self.started:
            return

        self._server.shutdown()
        self._server.server_close()
        self._server.socket.close()
        self._httpd_thread.join()
        self.started = False
        log.debug("Proxy: Stopped")
