from slyguy import plugin, gui, userdata, signals, inputstream
from slyguy.constants import ROUTE_LIVE_TAG
from slyguy.exceptions import Error
from slyguy.log import log

from .api import API
from .language import _
from .constants import HEADERS, TV_ID, MOVIES_ID
from .settings import settings


api = API()


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.TV,  _bold=True), path=plugin.url_for(menu, screen_id=TV_ID, title=_.TV))
        folder.add_item(label=_(_.MOVIES,  _bold=True), path=plugin.url_for(menu, screen_id=MOVIES_ID, title=_.MOVIES))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('profile_icon')}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)

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
    _select_profile()
    gui.refresh()

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _select_profile():
    account = api.account()
    profiles = account['profiles']

    options = []
    values = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': profile['avatar']['uri']}))

        if profile['id'] == userdata.get('profile_id'):
            default = index

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _set_profile(profile, notify=True):
    api.set_profile(profile['id'])

    if settings.getBool('kid_lockdown', False) and userdata.get('profile_kids'):
        userdata.set('kid_lockdown', True)

    if notify:
        gui.notification(_.PROFILE_ACTIVATED, heading=userdata.get('profile_name'), icon=userdata.get('profile_icon'))

@plugin.route()
def menu(screen_id, title=None, **kwargs):
    data = api.content(screen_id)
    folder = plugin.Folder(title or data['title'])

    #folder.add_item('Featured')

    for row in data['components'][0]['items']:
        folder.add_item(
            label = row['name'],
            path = plugin.url_for(content, screen_id=row['id']),
        )

    return folder

@plugin.route()
def content(screen_id, **kwargs):
    data = api.content(screen_id)
    folder = plugin.Folder(data['title'])
    folder.add_items(_parse_content(data['components'][0]['tiles']))
    return folder

def _parse_content(rows):
    items = []

    def _sort(x):
        for row in x.get('sortValues', []):
            if row['key'] == 'name':
                return row['value'].lower()

        return x['header'].lower()

    for row in sorted(rows, key=lambda  x: _sort(x)):
        if not row.get('contentItem'):
            row['contentItem'] = row['item']

        if row['contentItem']['isComingSoon'] or row['contentItem']['isRental']:
            continue

        if '/movie/' in row['contentItem']['path']:
            item = _parse_movie(row)
        elif '/series/' in row['contentItem']['path']:
            item = _parse_show(row)
        else:
            continue

        items.append(item)

    return items

def _parse_movie(row):
    return plugin.Item(
        label = row['header'],
        info = {
            'plot': row['contentItem']['summary'],
            'year': row['contentItem']['year'],
            'duration': row['contentItem']['duration']*60,
            'mediatype': 'movie',
        },
        art = {
            'thumb': row['image']['uri'] if isinstance(row['image'], dict) else row['image'],
            'fanart': row['contentItem']['keyart']['uri'],
        },
        playable = True,
        path = plugin.url_for(play, id=row['contentItem']['id']),
    )

def _parse_show(row):
    return plugin.Item(
        label = row['header'],
        info = {
            'plot': row['contentItem']['description'],
            'mediatype': 'tvshow',
        },
        art = {
            'thumb': row['image']['uri'] if isinstance(row['image'], dict) else row['image'],
            'fanart': row['contentItem']['keyart']['uri'],
        },
        path = plugin.url_for(show, path=row['contentItem']['path']),
    )

@plugin.route()
def show(path, **kwargs):
    show = api.content(path)['components'][0]['series']
    folder = plugin.Folder(show['title'])

    for season in show['seasons']:
        folder.add_item(
            label = _(_.SEASON, number=season['seasonNumber']),
            info = {
                'plot': season['description'],
                'mediatype': 'season',
            },
            art = {
                'thumb': show['tile']['image'],
                'fanart': show['keyart']['uri'],
            },
            path = plugin.url_for(episodes, path=show['path'], season_id=season['id']),
        )

    return folder

@plugin.route()
def episodes(path, season_id, **kwargs):
    show = api.content(path)['components'][0]['series']
    folder = plugin.Folder(show['title'], fanart=show['keyart']['uri'])

    for season in show['seasons']:
        if season['id'] == season_id:
            folder.add_items(_parse_episodes(show, season))
            break

    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    rows = api.search(query)
    return _parse_content(rows), False

def _parse_episodes(show, season):
    items = []

    for episode in season['episodes']:
        if episode['isComingSoon']:
            continue

        item = plugin.Item(
            label = episode['title'],
            info = {
                'title': episode['title'],
                'plot': episode['description'],
                'duration': episode['duration']*60,
                'tvshowtitle': show['title'],
                'mediatype': 'episode',
                'season' : int(episode['seasonNumber']),
                'episode': int(episode['episodeNumber']),
            },
            art = {
                'thumb': episode['images'][0]['uri'],
            },
            playable = True,
            path = plugin.url_for(play, id=episode['id']),
        )

        items.append(item)

    return items

@plugin.route()
@plugin.login_required()
def play(id, **kwargs):
    data = api.playback_auth(id)
    if 'errors' in data:
        msg = data['errors'][0]['message']
        plugin.exception(msg)

    try:
        referenceID = data['data']['playAuth']['reference_id']
        jwt_token = data['data']['playAuth']['drmToken']
        item = api.get_brightcove_src(referenceID, jwt_token)
        item.headers = HEADERS
        return item
    except Error as e:
        log.info("Error: {}. Fallback to data sources".format(e))

    streams = []
    for row in data['data']['playAuth']['sources']:
        stream = {'url': row['src'], 'license_url': None}
        if row['type'] == 'application/x-mpegURL':
            stream['type'] = 'hls'
        elif row['type'] == 'application/dash+xml':
            stream['type'] = 'dash'
        else:
            continue

        if row.get('key_systems'):
            if row['key_systems'].get('com.widevine.alpha'):
                stream['license_url'] = row['key_systems']['com.widevine.alpha']['license_url']
            else:
                continue

        if stream not in streams:
            streams.append(stream)

    streams = sorted(streams, key=lambda x: (x['type'] == 'hls' and not x['license_url'], x['type'] == 'dash'), reverse=True)
    if not streams:
        raise plugin.PluginError('No suitable stream found')

    headers = {}
    headers.update(HEADERS)
    headers['bcov-auth'] = data['data']['playAuth']['drmToken']

    selected = streams[0]
    item = plugin.Item(
        path = selected['url'],
        headers = headers,
    )

    if selected['license_url']:
        item.inputstream = inputstream.Widevine(
            license_key = selected['license_url']
        )

        if selected['type'] == 'hls':
            item.inputstream.manifest_type = 'hls'
            item.inputstream.mimetype = 'application/vnd.apple.mpegurl'

    elif selected['type'] == 'hls':
        item.inputstream = inputstream.HLS(live=ROUTE_LIVE_TAG in kwargs)

    else:
        item.inputstream = inputstream.MPD()

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    gui.refresh()
