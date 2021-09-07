from slyguy import plugin, gui, settings, userdata, inputstream, signals
from slyguy.log import log
from slyguy.constants import QUALITY_TAG, QUALITY_CUSTOM, QUALITY_ASK, QUALITY_BEST, QUALITY_LOWEST, QUALITY_TYPES
from slyguy.exceptions import FailedPlayback
from slyguy.util import get_system_arch, strip_html_tags

from .api import API
from .language import _
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.MY_COURSES, _bold=True), path=plugin.url_for(my_courses))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.my_courses(page=page, query=query)
    return _process_courses(data['results']), data['next']

@plugin.route()
def my_courses(page=1, **kwargs):
    page = int(page)
    folder = plugin.Folder(_.MY_COURSES)
    data = api.my_courses(page=page)
    items = _process_courses(data['results'])
    folder.add_items(items)

    if data['next']:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(my_courses, page=page+1),
        )

    return folder

def _process_courses(rows):
    items = []
    for row in rows:
        plot = _(_.COURSE_INFO,
            title = row['headline'],
            num_lectures = row['num_published_lectures'],
            percent_complete = row['completion_ratio'],
            length = row['content_info'],
        )

        item = plugin.Item(
            label = row['title'],
            path = plugin.url_for(chapters, course_id=row['id'], title=row['title']),
            art = {'thumb': row['image_480x270']},
            info = {'plot': plot},
            is_folder = True,
        )

        items.append(item)

    return items

@plugin.route()
def chapters(course_id, title, page=1, **kwargs):
    page = int(page)
    folder = plugin.Folder(title)

    rows, next_page = api.chapters(course_id, page=page)

    for row in sorted(rows, key=lambda r: r['object_index']):
        folder.add_item(
            label = _(_.SECTION_LABEL, section_number=row['object_index'], section_title=row['title']),
            path = plugin.url_for(lectures, course_id=course_id, chapter_id=row['id'], title=title),
            art = {'thumb': row['course']['image_480x270']},
            info = {'plot': strip_html_tags(row['description'])},
        )

    if next_page:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(chapters, course_id=course_id, title=title, page=page+1),
        )

    return folder

@plugin.route()
def lectures(course_id, chapter_id, title, page=1, **kwargs):
    page = int(page)
    folder = plugin.Folder(title)

    rows, next_page = api.lectures(course_id, chapter_id, page=page)

    for row in rows:
        folder.add_item(
            label = row['title'],
            path = plugin.url_for(play, asset_id=row['asset']['id']),
            art = {'thumb': row['course']['image_480x270']},
            info = {
                'title': row['title'],
                'plot': strip_html_tags(row['description']),
                'duration': row['asset']['length'],
                'mediatype': 'episode',
                'tvshowtitle': row['course']['title'],
            },
            playable = True,
        )

    if next_page:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(lectures, course_id=course_id, chapter_id=chapter_id, title=title, page=page+1),
        )

    return folder

def select_quality(qualities):
    options = []

    options.append([QUALITY_BEST, _.QUALITY_BEST])
    options.extend(qualities)
    options.append([QUALITY_LOWEST, _.QUALITY_LOWEST])

    values = [x[0] for x in options]
    labels = [x[1] for x in options]

    current = userdata.get('last_quality')

    default = -1
    if current:
        try:
            default = values.index(current)
        except:
            default = values.index(qualities[-1][0])

            for quality in qualities:
                if quality[0] <= current:
                    default = values.index(quality[0])
                    break

    index = gui.select(_.PLAYBACK_QUALITY, labels, preselect=default, autoclose=10000) #autoclose after 10seconds
    if index < 0:
        raise FailedPlayback('User cancelled quality select')

    userdata.set('last_quality', values[index])

    return values[index]

@plugin.route()
@plugin.login_required()
def play(asset_id, **kwargs):
    use_ia_hls = settings.getBool('use_ia_hls')
    stream_data = api.get_stream_data(asset_id)
    token = userdata.get('access_token')

    play_item = plugin.Item(
        art = False,
        headers = {'Authorization': 'Bearer {}'.format(token)},
        cookies = {'access_token': token, 'client_id': CLIENT_ID},
    )

    is_drm = stream_data.get('course_is_drmed', False)

    hls_url = stream_data.get('hls_url')
    if hls_url and not is_drm:
        play_item.path = hls_url
        play_item.inputstream = inputstream.HLS(live=False)
        return play_item

    stream_urls = stream_data.get('stream_urls') or {}
    streams = stream_urls.get('Video') or stream_urls.get('Audio') or []

    CODECS = {
        'libx264': 'H.264',
        'libx265': 'H.265',
    }

    urls = []
    qualities = []
    for item in streams:
        if item['type'] != 'application/x-mpegURL':
            try:
                data = stream_data['data']['outputs'][item['label']]
            except:
                data = {'migrated_from_non_labeled_conversions': True}

            if data.get('migrated_from_non_labeled_conversions'):
                bandwidth, resolution = BANDWIDTH_MAP.get(int(item['label']))
                codecs, fps = '', ''
            else:
                fps = _(_.QUALITY_FPS, fps=float(data['frame_rate']))
                resolution = '{}x{}'.format(data['width'], data['height'])
                bandwidth = data['video_bitrate_in_kbps'] * 1000 #(or total_bitrate_in_kbps)
                codecs = CODECS.get(data.get('video_codec'), '')

            urls.append([bandwidth, item['file']])
            qualities.append([bandwidth, _(_.QUALITY_BITRATE, bandwidth=float(bandwidth)/1000000, resolution=resolution, fps=fps, codecs=codecs)])

    if not urls:
        for row in stream_data.get('media_sources') or []:
            if row['type'] == 'application/x-mpegURL' and 'encrypted-files' not in row['src']:
                urls.append([row['src'], inputstream.HLS(live=False)])

            if row['type'] == 'application/dash+xml':
                play_item.path = row['src']

                if is_drm:
                    token = stream_data['media_license_token']
                    ia = inputstream.Widevine(license_key=WV_URL.format(token=token))
                else:
                    ia = inputstream.MPD()

                urls.append([row['src'], ia])

        if urls:
            urls = sorted(urls, key=lambda x: isinstance(x[1], inputstream.Widevine))
            play_item.path = urls[0][0]
            play_item.inputstream = urls[0][1]
            if isinstance(play_item.inputstream, inputstream.Widevine):
                system, arch = get_system_arch()
                if system == 'Windows' or (system == 'Linux' and arch == 'armv7'):
                    gui.ok(_.VMP_WARNING)

            return play_item

    if not urls:
        raise plugin.Error(_.NO_STREAM_ERROR)

    quality = kwargs.get(QUALITY_TAG)
    if quality is None:
        quality = settings.getEnum('default_quality', QUALITY_TYPES, default=QUALITY_ASK)
    else:
        quality = int(quality)

    urls = sorted(urls, key=lambda s: s[0], reverse=True)
    qualities = sorted(qualities, key=lambda s: s[0], reverse=True)

    if quality == QUALITY_CUSTOM:
        quality = int(settings.getFloat('max_bandwidth')*1000000)
    elif quality == QUALITY_ASK:
        quality = select_quality(qualities)

    if quality == QUALITY_BEST:
        quality = qualities[0][0]
    elif quality == QUALITY_LOWEST:
        quality = qualities[-1][0]

    play_item.path = urls[-1][1]
    for item in urls:
        if item[0] <= quality:
            play_item.path = item[1]
            break

    return play_item
