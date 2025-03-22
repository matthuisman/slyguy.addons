from kodi_six import xbmc
from collections import defaultdict
from six.moves.urllib_parse import unquote, urlparse, parse_qsl

from . import plugin, gui
from .inputstream import MPD
from .language import _
from .constants import ADDON_PROFILE, YOTUBE_PLUGIN_ID, ADDON_ID, IS_ANDROID, IS_PYTHON3, KODI_VERSION, MDBLIST_API_KEY
from .log import log
from .util import get_addon
from .settings import settings, YTMode, TrailerMode
from .session import Session


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
    return plugin.Item(path='plugin://{}/play/?video_id={}'.format(YOTUBE_PLUGIN_ID, video_id))    


def play_yt(video_id):
    log.debug("YouTube ID {}".format(video_id))

    if settings.YT_PLAY_USING.value == YTMode.PLUGIN and ADDON_ID != YOTUBE_PLUGIN_ID:
        return play_yt_plugin(video_id)

    if IS_ANDROID and settings.YT_PLAY_USING.value == YTMode.APK:
        return play_android_apk(video_id)

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


@plugin.route()
def play_youtube(video_id, **kwargs):
    return play_yt(video_id)


def li_trailer(listitem, ignore_trailer_path=False):
    vid_tag = listitem.getVideoInfoTag()
    trailer_path = vid_tag.getTrailer()
    media_type = vid_tag.getMediaType()
    title = listitem.getLabel()
    year = vid_tag.getYear()

    if ignore_trailer_path:
        trailer_path = ''

    if (YOTUBE_PLUGIN_ID in trailer_path.lower() or not trailer_path.lower().startswith('plugin')) and \
        (settings.TRAILER_MODE.value == TrailerMode.MDBLIST_MEDIA or (not trailer_path and settings.TRAILER_MODE.value != TrailerMode.MEDIA)):
        session = Session()

        providers = []
        unique_id = None
        if KODI_VERSION >= 20:
            for id_type in ('imdb', 'tvdb', 'tmdb'):
                unique_id = vid_tag.getUniqueID(id_type)
                if unique_id:
                    providers = [id_type]
                    break

        if not unique_id:
            unique_id = vid_tag.getIMDBNumber()
            if 'tt' in unique_id.lower():
                providers = ['imdb']
            elif media_type == 'movie':
                providers = ['tmdb']
            else:
                # can be tvdb or tmdb for shows
                providers = ['tvdb', 'tmdb']

        if not unique_id and settings.MDBLIST_SEARCH.value and title and year:
            log.info("mdblist search: {} ({})".format(title, year))
            data = session.get('https://api.mdblist.com/search/{}'.format('show' if media_type == 'tvshow' else 'movie'), params={'query': title, 'year': year, 'limit_by_score': 65, 'limit': 1, 'apikey': MDBLIST_API_KEY}).json()
            results = data['search']
            if results:
                log.info("mdblist search result: {}".format(results[0]))
                unique_id = results[0]['ids']['imdbid']
                providers = ['imdb']

        if unique_id:
            for provider in providers:
                data = session.get('https://api.mdblist.com/{}/{}/{}'.format(provider, 'show' if media_type == 'tvshow' else 'movie', unique_id), params={'apikey': MDBLIST_API_KEY}).json()
                trailer = data.get('trailer')
                if trailer and 'youtube' in trailer.lower():
                    log.info("mdblist trailer found: {}".format(trailer))
                    trailer_path = 'plugin://plugin.video.youtube/play/?video_id={}'.format(trailer.rsplit('=')[1])
                    break

    if not trailer_path:
        gui.notification(_.TRAILER_NOT_FOUND)
        return

    parsed = urlparse(trailer_path)
    if parsed.scheme.lower() == 'plugin':
        addon_id = parsed.netloc
        if addon_id.lower().strip() == YOTUBE_PLUGIN_ID and settings.YT_PLAY_USING.value != YTMode.PLUGIN:
            query_params = dict(parse_qsl(parsed.query))
            video_id = query_params.get('video_id') or query_params.get('videoid')
            trailer_path = plugin.url_for(play_youtube, video_id=video_id)
        else:
            # prompt to install if required
            get_addon(addon_id, required=True)

    li = plugin.Item(path=trailer_path)
    li.label = u"{} ({})".format(listitem.getLabel(), _.TRAILER)
    li.info = {
        'plot': vid_tag.getPlot(),
        'tagline': vid_tag.getTagLine(),
        'year': vid_tag.getYear(),
        'mediatype': vid_tag.getMediaType(),
    }

    try:
        # v20+
        li.info['genre'] = vid_tag.getGenres()
    except AttributeError:
        li.info['genre'] = vid_tag.getGenre()

    for key in ['thumb','poster','banner','fanart','clearart','clearlogo','landscape','icon']:
        li.art[key] = listitem.getArt(key)

    return li
