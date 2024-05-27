import sys
from collections import defaultdict

from kodi_six import xbmc
from six.moves.urllib_parse import unquote, parse_qsl

from slyguy import plugin, settings, inputstream
from slyguy.log import log
from slyguy.util import get_system_arch
from slyguy.constants import ADDON_PROFILE, ROUTE_CONTEXT


from .language import _


@plugin.route('/')
def home(**kwargs):
    if kwargs.get('action') == 'play_video':
        return plugin.redirect(plugin.url_for(play, video_id=kwargs.get('videoid')))

    folder = plugin.Folder()
    folder.add_item(label='TEST 4K', playable=True, path=plugin.url_for(play, video_id='NECyQhw4-_c'))
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

@plugin.route(ROUTE_CONTEXT)
def context(listitem, **kwargs):
    vid_tag = listitem.getVideoInfoTag()
    yt_url = vid_tag.getTrailer()
    params = dict(parse_qsl(yt_url.split('?')[1]))
    video_id = params.get('video_id') or params.get('videoid')
    if not video_id:
        raise plugin.PluginError(_(_.NO_VIDEO_ID_FOUND, url=yt_url))

    li = _play(video_id)
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

@plugin.route('/play')
def play(video_id, **kwargs):
    return _play(video_id)

def _play(video_id):
    log.debug("YouTube ID {}".format(video_id))

    is_android = get_system_arch()[0] == 'Android'
    if is_android and settings.getBool('play_with_youtube_apk', False):
        return play_android_apk(video_id)

    ydl_opts = {
        'quiet': True,
        'cachedir': ADDON_PROFILE,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios',] #['ios', 'android', 'web']
            }
        },
    }

    error = 'Unknown'
    try:
        from .yt_dlp import YoutubeDL
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
        if is_android and settings.getBool('fallback_youtube_apk', False):
            return play_android_apk(video_id)

        if sys.version_info[0] < 3:
            if is_android:
                error = _.PYTHON3_NOT_SUPPORTED_ANDROID
            else:
                error = _.PYTHON3_NOT_SUPPORTED
        else:
            error  = _(_.NO_VIDEOS_FOUND, id=video_id, error=error)

        raise plugin.PluginError(error)

    headers = {}
    str = '<MPD minBufferTime="PT1.5S" mediaPresentationDuration="PT{}S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011"><Period>'.format(data["duration"])
    for idx, (group, formats) in enumerate(groups.items()):
        str += '<AdaptationSet id="{}" mimeType="{}"><Role schemeIdUri="urn:mpeg:DASH:role:2011" value="main"/>'.format(idx, group)
        for format in formats:
            headers.update(format['http_headers'])
            format['url'] = unquote(format['url']).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            codec = format['vcodec'] if format['vcodec'] != 'none' else format['acodec']
            str += '<Representation id="{}" codecs="{}" bandwidth="{}"'.format(format["format_id"], codec, format["bitrate"])
            if format['vcodec'] != 'none':
                str += ' width="{}" height="{}" frameRate="{}/1001"'.format(format["width"], format["height"], format["fps"]*1000)
            str += '>'
            if format['acodec'] != 'none':
                str += '<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>'
            str += '<BaseURL>{}</BaseURL><SegmentBase indexRange="{}-{}"><Initialization range="{}-{}" /></SegmentBase>'.format(
                format["url"], format["indexRange"]["start"], format["indexRange"]["end"], format["initRange"]["start"], format["initRange"]["end"]
            )
            str += '</Representation>'
    
        str += '</AdaptationSet>'
    str += '</Period></MPD>'

    path = 'special://temp/yt.mpd'
    with open(xbmc.translatePath(path), 'w') as f:
        f.write(str)

    #TODO Subtitles
    return plugin.Item(
        path = path,
        slug = video_id,
        inputstream = inputstream.MPD(),
        headers = headers,
    )


# stub out search so tmdbhelper works
@plugin.route('/search')
def search(**kwargs):
    return plugin.Folder(no_items_label=_.NO_SEARCH_SUPPORT)
