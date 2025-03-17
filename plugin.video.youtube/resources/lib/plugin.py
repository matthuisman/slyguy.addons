import os
import sys
from collections import defaultdict

from kodi_six import xbmc
from six.moves.urllib_parse import unquote

from slyguy import plugin, inputstream
from slyguy.log import log
from slyguy.util import get_system_arch
from slyguy.constants import ADDON_PROFILE


from .language import _
from .settings import settings


@plugin.route('/')
def home(**kwargs):
    if kwargs.get('action') == 'play_video':
        return plugin.redirect(plugin.url_for(play, video_id=kwargs.get('videoid')))

    folder = plugin.Folder()
    folder.add_item(label='TEST 4K', info={'trailer': plugin.url_for(play, video_id='Q82tQJyJwgk')}, playable=True, path=plugin.url_for(play, video_id='Q82tQJyJwgk'))
    folder.add_item(label='TEST 4K HDR', playable=True, path=plugin.url_for(play, video_id='tO01J-M3g0U'))
    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
    return folder


def play_android_apk(video_id):
    # com.teamsmart.videomanager.tv, com.google.android.youtube, com.google.android.youtube.tv
    app_id = settings.get('android_app_id', '')
    intent = 'android.intent.action.VIEW'
   # yturl = 'vnd.youtube://www.youtube.com/watch?v={}'.format(video_id)
    yturl = 'https://www.youtube.com/watch?v={}'.format(video_id)
    start_activity = 'StartAndroidActivity({},{},,"{}")'.format(app_id, intent, yturl)
    log.debug(start_activity)
    xbmc.executebuiltin(start_activity)


@plugin.route('/play')
def play(video_id, **kwargs):
    log.debug("YouTube ID {}".format(video_id))

    is_android = get_system_arch()[0] == 'Android'
    if is_android and settings.PLAY_WITH_NATIVE_APK.value:
        return play_android_apk(video_id)

    if sys.version_info[0] < 3:
        if is_android:
            raise plugin.PluginError(_.PYTHON3_NOT_SUPPORTED_ANDROID)
        else:
            raise plugin.PluginError(_.PYTHON3_NOT_SUPPORTED)

    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'check_formats': False,
        'quiet': True,
        'cachedir': ADDON_PROFILE,
        'no_warnings': True,
    }

    if settings.COOKIES_PATH.value:
        ydl_opts['cookiefile'] = xbmc.translatePath(settings.COOKIES_PATH.value)

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    error = 'Unknown'
    try:
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info('https://www.youtube.com/watch?v={}'.format(video_id), download=False)
    except Exception as e:
        log.exception(e)
        error = e
        data = {}

    groups = defaultdict(list)
    for x in data.get('formats', []):
        if 'container' not in x:
            continue

        if x['container'] == 'webm_dash':
            if x['vcodec'] != 'none':
                groups['video/webm'].append(x)
            else:
                groups['audio/webm'].append(x)
        elif x['container'] == 'mp4_dash':
            groups['video/mp4'].append(x)
        elif x['container'] == 'm4a_dash':
            groups['audio/mp4'].append(x)

    if not groups:
        if is_android and settings.FALLBACK_YOUTUBE_APK.value:
            return play_android_apk(video_id)
        else:
            raise plugin.PluginError(_(_.NO_VIDEOS_FOUND, id=video_id, error=error))

    def fix_url(url):
        return unquote(url).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

    headers = {}
    str = '<MPD minBufferTime="PT1.5S" mediaPresentationDuration="PT{}S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011">\n<Period>'.format(data["duration"])
    for idx, (group, formats) in enumerate(groups.items()):
        for format in formats:
            original = default = ''
            if 'original' in format.get('format', '').lower():
                original = ' original="true"'
            if 'default' in format.get('format', '').lower():
                default = ' default="true"'

            str += '\n<AdaptationSet id="{}" mimeType="{}" lang="{}"{}{}><Role schemeIdUri="urn:mpeg:DASH:role:2011" value="main"/>'.format(idx, group, format['language'], original, default)
            headers.update(format['http_headers'])
            format['url'] = fix_url(format['url'])
            codec = format['vcodec'] if format['vcodec'] != 'none' else format['acodec']
            str += '\n<Representation id="{}" codecs="{}" bandwidth="{}"'.format(format["format_id"], codec, format["bitrate"])
            if format['vcodec'] != 'none':
                str += ' width="{}" height="{}" frameRate="{}/1001"'.format(format["width"], format["height"], format["fps"]*1000)
            str += '>'
            if format['acodec'] != 'none':
                str += '\n<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>'
            str += '\n<BaseURL>{}</BaseURL>\n<SegmentBase indexRange="{}-{}">\n<Initialization range="{}-{}" />\n</SegmentBase>'.format(
                format["url"], format["indexRange"]["start"], format["indexRange"]["end"], format["initRange"]["start"], format["initRange"]["end"]
            )
            str += '\n</Representation>'
            str += '\n</AdaptationSet>'

    if settings.SUBTITLES.value:
        for idx, lang in enumerate(data.get('subtitles', {})):
            vtt = [x for x in data['subtitles'][lang] if x['ext'] == 'vtt' and x.get('protocol') != 'm3u8_native']
            if not vtt:
                continue
            url = fix_url(vtt[0]['url'])
            str += '\n<AdaptationSet id="caption_{}" contentType="text" mimeType="text/vtt" lang="{}"'.format(idx, lang)
            str += '>\n<Representation id="caption_rep_{}">\n<BaseURL>{}</BaseURL>\n</Representation>\n</AdaptationSet>'.format(idx, url)

    if settings.AUTO_SUBTITLES.value:
        for idx, lang in enumerate(data.get('automatic_captions', {})):
            if 'orig' in lang.lower():
                continue
            vtt = [x for x in data['automatic_captions'][lang] if x['ext'] == 'vtt' and x.get('protocol') != 'm3u8_native']
            if not vtt:
                continue
            url = fix_url(vtt[0]['url'])
            str += '\n<AdaptationSet id="caption_{}" contentType="text" mimeType="text/vtt" lang="{}-({})"'.format(idx, lang, _.AUTO_TRANSLATE)
            str += '>\n<Representation id="caption_rep_{}">\n<BaseURL>{}</BaseURL>\n</Representation>\n</AdaptationSet>'.format(idx, url)

    str += '\n</Period>\n</MPD>'

    path = 'special://temp/yt.mpd'
    with open(xbmc.translatePath(path), 'w') as f:
        f.write(str)

    print(data['subtitles'])

    #TODO Subtitles
    return plugin.Item(
        path = path,
        slug = video_id,
        inputstream = inputstream.MPD(),
        headers = headers,
    )


# stub out search so tmdbhelper works
@plugin.route('/search')
@plugin.route('/kodion/search/query')
def search(**kwargs):
    log.warning("Youtube for Trailers does not support search ({}). Returning empty result".format(kwargs['_url']))
    return plugin.Folder(no_items_label=None, show_news=False)
