import re
from collections import defaultdict
from kodi_six import xbmc

from slyguy import plugin, gui, userdata, inputstream, signals
from slyguy.util import get_system_arch, strip_html_tags

from .api import API
from .language import _
from .constants import *
from .settings import settings


api = API()


def udemy_strip_html_tags(text):
    text = strip_html_tags(text)
    return re.sub(r'^\s+', '', text, flags=re.MULTILINE)


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
        folder.add_item(label=_(_.PURCHASED, _bold=True), path=plugin.url_for(purchased))
        folder.add_item(label=_(_.MY_LISTS, _bold=True), path=plugin.url_for(my_lists))
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
    data = api.search(page=page, query=query)
    items = _process_courses(data['courses'])
    return items, True


@plugin.route()
@plugin.pagination()
def my_lists(page=1, **kwargs):
    folder = plugin.Folder(_.MY_LISTS)
    data = api.collections()
    for row in data['results']:
        folder.add_item(
            label = '{} [{}]'.format(row['title'], row['num_courses']),
            info = {
                'plot': row['description'],
            },
            path = plugin.url_for(list, list_id=row['id'], label=row['title']),
        )
    return folder, data['next']


@plugin.route()
@plugin.pagination()
def list(list_id, label, page=1, **kwargs):
    folder = plugin.Folder(label)
    data = api.collection(list_id, page=page)
    items = _process_courses(data['results'])
    folder.add_items(items)
    return folder, data['next']


@plugin.route()
@plugin.pagination()
def purchased(page=1, **kwargs):
    folder = plugin.Folder(_.PURCHASED)
    data = api.purchased(page=page)
    items = _process_courses(data['results'])
    folder.add_items(items)
    return folder, data['next']


@plugin.route()
def edit_lists(course_id, **kwargs):
    course_id = int(course_id)
    data = api.collections()

    values = []
    options = []
    current = []
    for index, row in enumerate(data['results']):
        values.append(row['id'])
        options.append(row['title'])
        if course_id in [course['id'] for course in row['courses']]:
            current.append(index)

    selected = gui.select(_.EDIT_LISTS, options=options, preselect=current, multi=True)
    if selected is None:
        return

    to_add = []
    for index in selected:
        if index not in current:
            to_add.append(values[index])

    to_remove = []
    for index in current:
        if index not in selected:
            to_remove.append(values[index])
            api.del_collection_course(values[index], course_id)

    if not to_add and not to_remove:
        return

    total = len(to_add) + len(to_remove)
    count = 0
    with gui.progress(_.UPDATING_LISTS, background=True) as progress:
        # add new
        for list_id in to_add:
            count += 1
            progress.update(int((count/total)*100))
            api.add_collection_course(list_id, course_id)

        # remove old
        for list_id in to_remove:
            count += 1
            progress.update(int((count/total)*100))
            api.del_collection_course(to_remove, course_id)


def _process_courses(rows):
    items = []
    for row in rows:
        item = plugin.Item(
            label = row['title'],
            path = plugin.url_for(chapters, course_id=row['id'], title=row['title']),
            art = {'thumb': row['image_480x270']},
            info = {'plot': _(_.COURSE_INFO, headline=row['headline'])},
            is_folder = True,
            context = (
                (_.EDIT_LISTS, 'RunPlugin({})'.format(plugin.url_for(edit_lists, course_id=row['id']))),
            ),
        )

        items.append(item)

    return items


@plugin.route()
@plugin.pagination()
def chapters(course_id, title, page=1, **kwargs):
    folder = plugin.Folder(title)

    image = None
    total_lectures = 0
    rows, next_page = api.chapters(course_id, page=page)
    for row in sorted(rows, key=lambda r: r['object_index']):
        image = row['course']['image_480x270']

        plot = _(_.CHAPTER_INFO,
            description = udemy_strip_html_tags(row['description']),
            num_lectures = len(row['lectures']),
        )
        total_lectures += len(row['lectures'])

        folder.add_item(
            label = _(_.SECTION_LABEL, section_number=row['object_index'], section_title=row['title']),
            path = plugin.url_for(lectures, course_id=course_id, title=title, chapter_id=row['id']),
            art = {'thumb': image},
            info = {'plot': plot},
        )

    folder.add_item(
        label = _(_.ALL, _bold=True),
        path = plugin.url_for(lectures, course_id=course_id, title=title),
        art = {'thumb': image},
        info = {'plot':_(_.CHAPTER_INFO, description='', num_lectures=total_lectures)},
        specialsort = 'top',
        _position = 0,
    )

    return folder, next_page


@plugin.route()
@plugin.pagination()
def lectures(course_id, title, chapter_id=None, page=1, **kwargs):
    folder = plugin.Folder(title)

    ep_nums = defaultdict(int)
    rows, next_page = api.lectures(course_id, page=page)
    for row in rows:
        if chapter_id and int(chapter_id) != int(row['chapter']['id']):
            continue

        ep_nums[row['chapter']['object_index']] += 1
        plot = u'[B]{}[/B]\n\n{}'.format(row['chapter']['title'], udemy_strip_html_tags(row['description']))
        folder.add_item(
            label = row['title'],
            path = plugin.url_for(play, asset_id=row['asset']['id']),
            art = {'thumb': row['course']['image_480x270']},
            info = {
                'title': row['title'],
                'plot': plot,
                'season': row['chapter']['object_index'],
                'episode': ep_nums[row['chapter']['object_index']],
                'duration': row['asset']['length'],
                'mediatype': 'episode',
                'tvshowtitle': row['course']['title'],
            },
            playable = True,
        )

    return folder, next_page


@plugin.route()
@plugin.login_required()
def play(asset_id, **kwargs):
    stream_data = api.get_stream_data(asset_id)
    token = userdata.get('access_token')
    headers = {'Authorization': 'Bearer {}'.format(token), 'user-agent': 'python-requests/2.28.2'}

    play_item = plugin.Item(
        headers = headers,
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
        'libx264': 'avc',
        'libx265': 'hvc',
    }

    mp4s = []
    adaptives = []
    for item in streams:
        if item['type'] != 'application/x-mpegURL':
            try:
                data = stream_data['data']['outputs'][item['label']]
            except:
                data = {'migrated_from_non_labeled_conversions': True}

            if data.get('migrated_from_non_labeled_conversions'):
                bandwidth, resolution = BANDWIDTH_MAP.get(int(item['label']))
                codecs, fps = 'avc', '30'
            else:
                fps = _(_.QUALITY_FPS, fps=float(data['frame_rate']))
                resolution = '{}x{}'.format(data['width'], data['height'])
                bandwidth = data['video_bitrate_in_kbps'] * 1000 #(or total_bitrate_in_kbps)
                codecs = CODECS.get(data.get('video_codec'), '')

            mp4s.append([bandwidth, resolution, fps, codecs, item['file']])

    for row in stream_data.get('media_sources') or []:
        if row['type'] == 'application/x-mpegURL' and 'encrypted-files' not in row['src']:
            adaptives.append([row['src'], inputstream.HLS(live=False)])

        elif row['type'] == 'video/mp4':
            bandwidth, resolution = BANDWIDTH_MAP.get(int(row['label']))
            mp4s.append([bandwidth, resolution, '30', 'avc', row['src']])

        if row['type'] == 'application/dash+xml':
            play_item.path = row['src']

            if is_drm:
                token = stream_data['media_license_token']
                ia = inputstream.Widevine(license_key=WV_URL.format(token=token))
            else:
                ia = inputstream.MPD()

            adaptives.append([row['src'], ia])

    if mp4s:
        play_item.path = 'special://temp/udemy.m3u8'
        play_item.proxy_data['custom_quality'] = True
        with open(xbmc.translatePath(play_item.path), 'w') as f:
            f.write('#EXTM3U\n#EXT-X-VERSION:3\n')
            for row in mp4s:
                f.write('\n#EXT-X-STREAM-INF:BANDWIDTH={},RESOLUTION={},FRAME-RATE={},CODECS={}\n{}'.format(row[0], row[1], row[2], row[3], row[4]))

    elif adaptives:
        adaptives = sorted(adaptives, key=lambda x: isinstance(x[1], inputstream.Widevine))
        play_item.path = adaptives[0][0]
        play_item.inputstream = adaptives[0][1]
        if isinstance(play_item.inputstream, inputstream.Widevine):
            system, arch = get_system_arch()
            if system == 'Windows' or (system == 'Linux' and arch == 'armv7'):
                if not gui.ok(_.VMP_WARNING):
                    return

    else:
        raise plugin.Error(_.NO_STREAM_ERROR)

    return play_item
