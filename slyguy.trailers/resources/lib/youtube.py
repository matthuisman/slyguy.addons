import os
import sys
from collections import defaultdict

from kodi_six import xbmc, xbmcaddon
from six.moves.urllib_parse import unquote, urlparse, parse_qsl

from slyguy import plugin
from slyguy.inputstream import MPD
from slyguy.constants import IS_ANDROID, IS_PYTHON3, ADDON_PROFILE, ADDON_ID
from slyguy.log import log
from slyguy.util import get_addon

from .constants import YOTUBE_PLUGIN_ID, TUBED_PLUGIN_ID
from .settings import settings
from .language import _

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def get_youtube_id(url):
    if not url or not is_youtube_url(url):
        return

    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query))
    return query_params.get('video_id') or query_params.get('videoid') or query_params.get('v')


def is_youtube_url(url):
    return ADDON_ID.lower() in url or YOTUBE_PLUGIN_ID.lower() in url.lower() or TUBED_PLUGIN_ID.lower() in url.lower() or 'youtube.com' in url.lower()


def play_youtube(video_id):
    if settings.YT_APK.value:
        return play_yt_apk(video_id)
    elif settings.YT_DLP.value:
        return play_yt_dlp(video_id)
    else:
        return play_yt_plugin(video_id)


def play_yt_dlp(video_id):
    if not IS_PYTHON3:
        if IS_ANDROID:
            raise plugin.PluginError(_.PYTHON2_NOT_SUPPORTED_ANDROID)
        else:
            raise plugin.PluginError(_.PYTHON2_NOT_SUPPORTED)

    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'check_formats': False,
        'quiet': True,
        'cachedir': ADDON_PROFILE,
       # 'no_warnings': True,
    }

    if settings.YT_COOKIES_PATH.value:
        ydl_opts['cookiefile'] = xbmc.translatePath(settings.YT_COOKIES_PATH.value)

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
        raise plugin.PluginError(_(_.NO_VIDEOS_FOUND_FOR_YT, id=video_id, error=error))

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

    return plugin.Item(
        path = path,
        slug = video_id,
        inputstream = MPD(),
        headers = headers,
    )


def play_yt_apk(video_id):
    app_id = settings.YT_APK_ID.value  # com.teamsmart.videomanager.tv, com.google.android.youtube, com.google.android.youtube.tv
    intent = 'android.intent.action.VIEW'
    yturl = 'https://www.youtube.com/watch?v={}'.format(video_id) # yturl = 'vnd.youtube://www.youtube.com/watch?v={}'.format(video_id)
    start_activity = 'StartAndroidActivity({},{},,"{}")'.format(app_id, intent, yturl)
    log.debug(start_activity)
    xbmc.executebuiltin(start_activity)


def has_addon(addon_id):
    addon = get_addon(addon_id, install=False, required=False)
    if addon:
        return addon.getAddonInfo('author').lower() != 'slyguy'
    return False


def assert_not_slyguy(addon_id):
    if xbmcaddon.Addon(addon_id).getAddonInfo('author').lower() == 'slyguy':
        raise plugin.PluginError(_(_.PLAYBACK_IS_REDIRECT_ERROR, addon_id=addon_id))


def play_yt_plugin(video_id):
    if has_addon(TUBED_PLUGIN_ID):
        return plugin.Item(path='plugin://{}/?mode=play&video_id={}'.format(TUBED_PLUGIN_ID, video_id))

    get_addon(YOTUBE_PLUGIN_ID, install=True, required=True)
    assert_not_slyguy(YOTUBE_PLUGIN_ID)
    return plugin.Item(path='plugin://{}/play/?video_id={}'.format(YOTUBE_PLUGIN_ID, video_id))
