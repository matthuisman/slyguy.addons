from kodi_six import xbmc
from collections import defaultdict
from six.moves.urllib_parse import unquote

from .plugin import Item, PluginError
from .inputstream import MPD
from .language import _
from .constants import ADDON_PROFILE, YOTUBE_PLUGIN_ID, ADDON_ID, IS_ANDROID, IS_PYTHON3
from .log import log
from .util import get_addon
from .settings import settings, YTMode


def play_android_apk(video_id):
    # com.teamsmart.videomanager.tv, com.google.android.youtube, com.google.android.youtube.tv
    app_id = settings.YT_NATIVE_APK_ID.value
    intent = 'android.intent.action.VIEW'
   # yturl = 'vnd.youtube://www.youtube.com/watch?v={}'.format(video_id)
    yturl = 'https://www.youtube.com/watch?v={}'.format(video_id)
    start_activity = 'StartAndroidActivity({},{},,"{}")'.format(app_id, intent, yturl)
    log.debug(start_activity)
    xbmc.executebuiltin(start_activity)


def play_yt_plugin(video_id):
    get_addon(YOTUBE_PLUGIN_ID, required=True)
    return Item(path='plugin://{}/play/?video_id={}'.format(YOTUBE_PLUGIN_ID, video_id))    


def play_yt(video_id):
    log.debug("YouTube ID {}".format(video_id))

    if settings.YT_PLAY_USING.value == YTMode.PLUGIN and ADDON_ID != YOTUBE_PLUGIN_ID:
        return play_yt_plugin(video_id)

    if IS_ANDROID and settings.YT_PLAY_USING.value == YTMode.APK:
        return play_android_apk(video_id)

    if not IS_PYTHON3:
        if IS_ANDROID:
            raise PluginError(_.PYTHON2_NOT_SUPPORTED_ANDROID)
        else:
            raise PluginError(_.PYTHON2_NOT_SUPPORTED)

    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'check_formats': False,
        'quiet': True,
        'cachedir': ADDON_PROFILE,
        'no_warnings': True,
    }

    if settings.YT_COOKIES_PATH.value:
        ydl_opts['cookiefile'] = xbmc.translatePath(settings.YT_COOKIES_PATH.value)

    error = 'Unknown'
    try:
        #TODO: register our RequestHandler to use our Session()!
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
        if IS_ANDROID and settings.YT_PLAY_USING.value == YTMode.YT_DLP_APK:
            return play_android_apk(video_id)
        elif settings.YT_PLAY_USING.value == YTMode.YT_DLP_PLUGIN and ADDON_ID != YOTUBE_PLUGIN_ID:
            return play_yt_plugin(video_id)
        else:
            raise PluginError(_(_.NO_VIDEOS_FOUND_FOR_YT, id=video_id, error=error))

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

    if settings.YT_SUBTITLES.value:
        for idx, lang in enumerate(data.get('subtitles', {})):
            vtt = [x for x in data['subtitles'][lang] if x['ext'] == 'vtt' and x.get('protocol') != 'm3u8_native']
            if not vtt:
                continue
            url = fix_url(vtt[0]['url'])
            str += '\n<AdaptationSet id="caption_{}" contentType="text" mimeType="text/vtt" lang="{}"'.format(idx, lang)
            str += '>\n<Representation id="caption_rep_{}">\n<BaseURL>{}</BaseURL>\n</Representation>\n</AdaptationSet>'.format(idx, url)

    if settings.YT_AUTO_SUBTITLES.value:
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

    return Item(
        path = path,
        slug = video_id,
        inputstream = MPD(),
        headers = headers,
    )
