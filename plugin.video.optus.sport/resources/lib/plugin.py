import codecs

import arrow

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_LIVE_TAG, ROUTE_LIVE_SUFFIX

from .api import API
from .language import _
from .constants import HEADERS, DEFAULT_IMG, LINEAR_ID

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
        folder.add_item(label=_(_.CHANNELS, _bold=True), path=plugin.url_for(editorial, id=LINEAR_ID, title=_.CHANNELS))
        _home(folder)

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _home(folder):
    for row in api.navigation():
        if row['id'] == 'teams':
            continue

        if row['id'] == 'home':
            row['title'] = _.FEATURED

        folder.add_item(
            label = _(row['title'], _bold=True),
            path  = plugin.url_for(page, id=row['path'], title=row['title']),
        )

@plugin.route()
def page(id, title, **kwargs):
    folder = plugin.Folder(title)

    for row in api.page(id):
        folder.add_item(
            label = row['title'],
            path  = plugin.url_for(editorial, id=row['id'], title=row['title']),
        )

    return folder

@plugin.route()
def editorial(id, title, **kwargs):
    folder = plugin.Folder(title)

    alerts = userdata.get('alerts', [])
    now    = arrow.utcnow()

    live_play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

    for row in api.editorial(id):
        is_live = row.get('isLive', False)
        is_linear = row.get('type') == 'linear-channel'

        item = plugin.Item(
            label = row['title'],
            info  = {
                'plot': row.get('description'),
                'duration': row.get('duration', 0),
            },
            art   = {'thumb': row.get('imageUrl') or DEFAULT_IMG},
            path  = plugin.url_for(play, asset=row['id'], _is_live=is_live),
            playable = True,
            is_folder = False,
        )

        start_time = arrow.get(row['broadcastStartTime']) if 'broadcastStartTime' in row else None

        if start_time and start_time > now:
            item.label += start_time.to('local').format(_.DATE_FORMAT)
            item.path  = plugin.url_for(alert, asset=row['id'], title=row['title'])
            item.playable = False

            if row['id'] not in alerts:
                item.info['playcount'] = 0
            else:
                item.info['playcount'] = 1

        elif is_linear:
            item.path = plugin.url_for(play, asset=row['id'], _is_live=is_live)

        elif is_live:
            item.label = _(_.LIVE, label=item.label)

            item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
                plugin.url_for(play, asset=row['id'], play_type=PLAY_FROM_LIVE, _is_live=is_live)
            )))

            item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
            plugin.url_for(play, asset=row['id'], play_type=PLAY_FROM_START, _is_live=is_live)
            )))

            item.path = plugin.url_for(play, asset=row['id'], play_type=live_play_type, _is_live=is_live)

        folder.add_items(item)

    return folder

@plugin.route()
def alert(asset, title, **kwargs):
    alerts = userdata.get('alerts', [])

    if asset not in alerts:
        alerts.append(asset)
        gui.notification(title, heading=_.REMINDER_SET)
    else:
        alerts.remove(asset)
        gui.notification(title, heading=_.REMINDER_REMOVED)

    userdata.set('alerts', alerts)
    gui.refresh()

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

@plugin.route()
@plugin.login_required()
def play(asset, play_type=PLAY_FROM_LIVE, **kwargs):
    play_type = int(play_type)

    from_start = False
    if play_type == PLAY_FROM_START or (play_type == PLAY_FROM_ASK and not gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START)):
        from_start = True

    stream = api.play(asset, True)

    item = plugin.Item(
        path        = stream['url'],
        inputstream = inputstream.Widevine(license_key=stream['license']['@uri']),
        headers     = HEADERS,
    )

    drm_data = stream['license'].get('drmData')
    if drm_data:
        item.headers['x-axdrm-message'] = drm_data

    if from_start:
        item.properties['ResumeTime'] = '1'
        item.properties['TotalTime']  = '1'

    if kwargs.get(ROUTE_LIVE_TAG):
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

@signals.on(signals.ON_SERVICE)
def service():
    alerts = userdata.get('alerts', [])
    if not alerts:
        return

    now     = arrow.now()
    notify  = []
    _alerts = []

    for id in alerts:
        asset = api.asset(id)
        if 'broadcastStartTime' not in asset:
            continue

        start = arrow.get(asset['broadcastStartTime'])

        if now > start and (now - start).total_seconds() <= 60*10:
            notify.append(asset)
        elif now < start:
            _alerts.append(id)

    userdata.set('alerts', _alerts)

    for asset in notify:
        if not gui.yes_no(_(_.EVENT_STARTED, event=asset['title']), yeslabel=_.WATCH, nolabel=_.CLOSE):
            continue

        with signals.throwable():
            play(asset['id'])

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in api.editorial(LINEAR_ID):
            if row.get('type') != 'linear-channel':
                continue

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                id=row['channel']['id'], logo=row.get('imageUrl') or DEFAULT_IMG, name=row['title'], path=plugin.url_for(play, asset=row['id'], _is_live=True)))