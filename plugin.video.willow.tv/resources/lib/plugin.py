import json

import arrow

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START

from .api import API
from .language import _
from .constants import HEADERS, TEAMS_IMAGE_URL

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
        folder.add_item(label=_(_.LIVE, _bold=True), path=plugin.url_for(live))
        folder.add_item(label=_(_.PLAYED, _bold=True), path=plugin.url_for(played))
        folder.add_item(label=_(_.UPCOMING, _bold=True), path=plugin.url_for(upcoming))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE, no_items_label=_.NO_MATCHES)

    data = api.live_matches()
    for row in data['live']:
        start = arrow.get(row['match_start_date']).to('local').format(_.DATE_FORMAT)

        sources  = row['stream']['video_sources']
        priority = sources[0]['priority']

        item = plugin.Item(
            label    = row['subtitle'],
            info     = {'plot': _(_.MATCH_PLOT, series=row['seriesName'], match=row['subtitle'], start=start)},
            art      = {'thumb': TEAMS_IMAGE_URL.format(team1=row['team1'], team2=row['team2']).replace(' ', '')},
            path     = plugin.url_for(play_live, match_id=row['mid'], priority=priority),
            playable = True,
        )

        if len(sources) > 1:
            url = plugin.url_for(select_source, match_id=row['mid'], sources=json.dumps(sources))
            item.context.append((_.PLAYBACK_SOURCE, 'PlayMedia({})'.format(url)))

        folder.add_items(item)

    return folder

@plugin.route()
def select_source(match_id, sources, **kwargs):
    match_id = int(match_id)

    sources = json.loads(sources)

    options = [x['priority'] for x in sources]
    labels = [x['title'] for x in sources]

    index = gui.select(_.PLAYBACK_SOURCE, options=labels)
    if index < 0:
        return

    priority = int(options[index])

    url = api.play_live(match_id, priority)
    return _play(url)

@plugin.route()
def played(**kwargs):
    folder = plugin.Folder(_.PLAYED, no_items_label=_.NO_MATCHES)

    data = api.played_series()
    for row in data['vod']:
        folder.add_item(
            label = row['title'],
            art = {'thumb': row['img']},
            path = plugin.url_for(series, series_id=row['sid']),
        )

    return folder

@plugin.route()
def series(series_id, **kwargs):
    series_id = int(series_id)

    data = api.get_series(series_id)
    folder = plugin.Folder(data['title'])

    for row in data['matches']:
        start = arrow.get(row['match_start_date']).to('local').format(_.DATE_FORMAT)

        thumb = TEAMS_IMAGE_URL.format(team1=row['team1'], team2=row['team2']).replace(' ', '')

        folder.add_item(
            label = row['subtitle'],
            art = {'thumb': thumb},
            info = {'plot': _(_.MATCH_PLOT, series=row['seriesName'], match=row['subtitle'], start=start)},
            path = plugin.url_for(match, title=row['subtitle'], thumb=thumb, match_id=row['mid']),
        )

    return folder

@plugin.route()
def match(match_id, title='', thumb='', index=None, **kwargs):
    match_id = int(match_id)

    data = api.match(match_id)
    folder = plugin.Folder(title)

    if not index:
        for row in data['match']:
            folder.add_item(
                label = row['title'],
                path  = plugin.url_for(match, match_id=match_id, title=title, index=row['catIndex']),
            )

        return folder

    videos = []
    for row in data['match']:
        if row['catIndex'] == index:
            videos = row[row['catIndex']]

    for row in videos:
        if 'plId' in row:
            ids = [row['plId'],]
        elif 'Ids' in row:
            ids = row['Ids']
        else:
            ids = [None,]

        for count, id in enumerate(ids):
            if id == None:
                path = None
            elif index == 'highlight':
                path = plugin.url_for(play_highlight, match_id=match_id, content_id=id)
            elif index == 'replay':
                path = plugin.url_for(play_replay, match_id=match_id, content_id=id)
            else:
                path = None

            label = row['title']
            if len(ids) > 1:
                label = _(_.MULTIPART_VIDEO, label=label, part=count+1)

            folder.add_item(
                label = label,
                art = {'thumb': row['img']},
                path = path,
                playable = path != None,
                is_folder = False,
            )

    return folder

@plugin.route()
def play_live(match_id, priority=1, **kwargs):
    return _play_live(match_id, priority)

def _play_live(match_id, priority=1):
    match_id = int(match_id)
    priority = int(priority)
    url = api.play_live(match_id, priority)
    return _play(url, live=True)

@plugin.route()
def play_highlight(match_id, content_id, **kwargs):
    match_id = int(match_id)
    content_id = int(content_id)
    url = api.play_highlight(match_id, content_id)
    return _play(url)

@plugin.route()
def play_replay(match_id, content_id, **kwargs):
    match_id = int(match_id)
    content_id = int(content_id)
    url = api.play_replay(match_id, content_id)
    return _play(url)

def _play(url, live=False):
    return plugin.Item(
        path = url,
        headers = HEADERS,
        inputstream = inputstream.HLS(live=live),
    )

@plugin.route()
def upcoming(**kwargs):
    folder = plugin.Folder(_.UPCOMING, no_items_label=_.NO_MATCHES)

    data = api.upcoming_matches()
    for row in data['upcoming']:
        start = arrow.get(row['startDateTime']).to('local').format(_.DATE_FORMAT)

        if row['team1'] == 'TBC' or row['team2'] == 'TBC':
            thumb = None
        else:
            thumb = TEAMS_IMAGE_URL.format(team1=row['team1'], team2=row['team2']).replace(' ', '')

        item = plugin.Item(
            label = _(_.UPCOMING_MATCH, label=row['subtitle'], start=start),
            art = {'thumb': thumb},
            info = {'plot': _(_.MATCH_PLOT, series=row['seriesName'], match=row['subtitle'], start=start)},
            path = plugin.url_for(play_live, match_id=row['mid']),
            playable = True,
        )

        folder.add_items(item)

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
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
