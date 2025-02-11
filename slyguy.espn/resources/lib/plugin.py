import arrow
from slyguy import plugin, gui, signals, inputstream, userdata
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor
from slyguy.exceptions import PluginError
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_START, ROUTE_LIVE_TAG

from .language import _
from .api import API
from .constants import PROVIDER_LOGIN_URL, ESPN_LOGIN_URL
from .settings import settings


api = API()


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in


@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(account), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE, _bold=True), path=plugin.url_for(live))
        folder.add_item(label=_(_.UPCOMING, _bold=True), path=plugin.url_for(upcoming))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.ACCOUNT, path=plugin.url_for(account), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
    return folder


@plugin.route()
def live(**kwargs):
    return _events(_.LIVE, status='live')


@plugin.route()
def upcoming(**kwargs):
    return _events(_.UPCOMING, status='upcoming')


def _events(label, status):
    folder = plugin.Folder(label)

    rows = api.home()['buckets']

    events = []
    for row in rows:
        if 'featured' not in row['name'].lower():
            if status == 'live' and 'live' not in row['name'].lower():
                continue
            elif status == 'upcoming' and 'upcoming' not in row['name'].lower():
                continue

        events = [x for x in row['contents'] if x.get('status') == status]
        if len(events) == row['metadata']['displayCount'] and row['metadata']['displayCount'] != row['metadata']['totalCount']:
            row['contents'] = api.bucket(row['id'])['buckets'][0]['contents']
            events = [x for x in row['contents'] if x.get('status') == status]
        items = _process_events(events)
        folder.add_items(items)

    return folder

def _process_events(rows):
    avail_auth = []
    if api.provider.logged_in:
        avail_auth.append('mvpd')
    if api.espn.logged_in:
        avail_auth.append('direct')

    hidden = userdata.get('hidden', [])
    show_scores = settings.getBool('show_live_scores', False)
    whitelist = [x.lower().strip() for x in settings.get('sport_whitelist').split(',') if x.strip()]
    now = arrow.now().to('local')

    items = []
    events = []
    for row in sorted(rows, key=lambda x: x['utc']):
        if row['id'] in events or row.get('eventId') in events:
            continue

        streams = []
        for stream in row['streams']:
            if 'direct' not in stream['authTypes'] and stream['source']['id'] in hidden:
                continue

            if any(x in stream['authTypes'] for x in avail_auth):
                streams.append(stream)

        if not streams:
            continue

        catalog = {}
        for cat in row.get('catalog', []):
            catalog[cat['type']] = cat['name']

        sport = catalog.get('sport','').strip()
        league = catalog.get('league','').strip()
        if whitelist and (sport or league):
            allow = False
            for allowed in whitelist:
                if allowed in sport.lower() or allowed in league.lower():
                    allow = True
                    break

            if not allow:
                continue

        sport = u'{} - {}'.format(catalog.get('sport' ,''), catalog.get('league', '')).strip().strip('-').strip()
        if sport:
            sport = u'({})'.format(sport)
        label = u'{name} {sport} '.format(name=row['name'], sport=sport).strip()

        start = arrow.get(row['utc']).to('local')
        if start.format('DDDD') == now.format('DDDD'):
            starts = start.format('h:mm A')
        else:
            starts = start.format('MMM Do h:mm A')

        if row['status'] != 'live':
            label += u' [B][{}][/B]'.format(starts)

        plot = row['subtitle']
        if start < now:
            plot += '\n' + _(_.STARTED, time=starts)
        else:
            plot += '\n' + _(_.STARTS, time=starts)

        if row.get('eventId'):
            path = plugin.url_for(play, event_id=row['eventId'], _is_live=True)
            if 'event' in row and show_scores:
                plot += u'\n\n{statusTextOne}\n{teamOneName} {teamOneScore}\n{teamTwoName} {teamTwoScore}'.format(**row['event'])
        else:
            path = plugin.url_for(play, content_id=row['id'], _is_live=True)

        if row.get('eventId'):
            events.append(row['eventId'])
        events.append(row['id'])

        item = plugin.Item(
            label = label,
            info = {
                'plot': plot,
            },
            art = {'thumb': row['imageHref']},
            playable = True,
            path = path,
        )

        if 'direct' not in streams[0]['authTypes']:
            item.context = [(_.HIDE_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(hide_channel, id=streams[0]['source']['id']))),]

        items.append(item)

    return items


@plugin.route()
def hide_channel(id, **kwargs):
    hidden = userdata.get('hidden', [])
    if id not in hidden:
        hidden.append(id)
    userdata.set('hidden', hidden)
    gui.refresh()


@plugin.route()
def account(**kwargs):
    options = []
    funcs = []

    if not api.provider.logged_in:
        options.append(_(_.PROVIDER_LOGIN, _bold=True))
        funcs.append(_provider_login)
    else:
        options.append(_.PROVIDER_LOOUT)
        funcs.append(_provider_logout)

    if not api.espn.logged_in:
        options.append(_(_.ESPN_LOGIN, _bold=True))
        funcs.append(_espn_login)
    else:
        options.append(_.ESPN_LOGOUT)
        funcs.append(_espn_logout)

    index = gui.select(options=options, heading=_.ACCOUNT)
    if index < 0:
        return

    if funcs[index]():
        gui.refresh()

def _espn_login(**kwargs):
    timeout = 600
    with api.espn.login() as login_progress:
        with gui.progress(_(_.ESPN_LOGIN_STEPS, url=ESPN_LOGIN_URL, code=login_progress.code), heading=_.ESPN_LOGIN) as progress:
            for i in range(timeout):
                if progress.iscanceled() or not login_progress.is_alive() or monitor.waitForAbort(1):
                    break

                progress.update(int((i / float(timeout)) * 100))

            login_progress.stop()
            return login_progress.result

def _provider_login(**kwargs):
    with api.provider.login() as data:
        # Countries that support TV Provider login natively
        if api.geo().upper() in ('US',):
            instructions = _(_.ESPN_LOGIN_STEPS, url=ESPN_LOGIN_URL, code=data['code'])
        # Use TV Provider MJH workaround
        else:
            instructions = _(_.PROVIDER_LOGIN_STEPS, url=PROVIDER_LOGIN_URL, code=data['code'])

        with gui.progress(instructions, heading=_.PROVIDER_LOGIN) as progress:
            timeout = int((data['expires'] - data['generated']) / 1000)
            for i in range(timeout):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    break

                progress.update(int((i / float(timeout)) * 100))

                if i % 5 == 0 and api.provider.authenticate(data['device_id']):
                    return True

def _espn_logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO, heading=_.ESPN_LOGOUT):
        return

    api.espn.logout()
    return True

def _provider_logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO, heading=_.PROVIDER_LOOUT):
        return

    api.provider.logout()
    return True

@plugin.route()
@plugin.login_required()
def play(content_id=None, event_id=None, network_id=None, **kwargs):
    is_live = ROUTE_LIVE_TAG in kwargs

    if event_id:
        stream = _select_stream(event_id)
        if stream:
            content_id = stream['id']
            is_live = stream['status'].lower() == 'live'

    elif network_id:
        stream = api.play_network(network_id)
        content_id = stream['id']

    if not content_id:
        raise PluginError(_.NO_SOURCE)

    airing, playback_data = api.play(content_id)

    item = plugin.Item(
        path = playback_data['url'],
        headers = playback_data.get('headers'),
    )

    if playback_data['type'] == 'DASH_WIDEVINE':
        item.inputstream = inputstream.Widevine(license_key=playback_data.get('license_url'))
    else:
        item.inputstream = inputstream.HLS(live=is_live)

    offset = int((arrow.get(airing['startDateTime']) - arrow.now()).total_seconds())
    if is_live and not airing.get('requiresLinearPlayback', True) and offset < 0:
        play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)
        if play_type == PLAY_FROM_ASK:
            result = plugin.live_or_start()
            if result == -1:
                return
            elif result == 1:
                item.resume_from = offset

        elif play_type == PLAY_FROM_START:
            item.resume_from = offset

    return item

def _select_stream(event_id):
    options = []
    values = []

    avail_auth = []
    if api.provider.logged_in:
        avail_auth.append('mvpd')
    if api.espn.logged_in:
        avail_auth.append('direct')

    hidden = userdata.get('hidden', [])
    alt_lang = settings.getBool('alt_languages', True)

    groups = []
    for group in api.picker(event_id):

        if not alt_lang and group['name'].lower().startswith('watch in'):
            continue

        streams = []
        for row in group.get('contents', []):
            if not row.get('streams'):
                continue

            stream = row['streams'][0]
            if 'direct' not in stream['authTypes'] and stream['source']['id'] in hidden:
                continue
            if not any(x in stream['authTypes'] for x in avail_auth):
                continue

            streams.append(stream)

        if streams:
            name = group['name']
            if all([x['status'].lower() == 'live' for x in streams]):
                name += ' ' + _.LIVE_EVENT
            if all([x['status'].lower() == 'replay' for x in streams]):
                name += ' ' + _.REPLAY_EVENT
            groups.append([name, streams])

    if not groups:
        return None

    if len(groups) > 1:
        index = gui.context_menu([x[0] for x in groups])
        if index < 0:
            return
        groups = [groups[index]]

    for index, row in enumerate(groups):
        for stream in row[1]:
            name = stream['name']
            if stream['status'].lower() == 'live':
                name += ' ' + _.LIVE_EVENT
            elif stream['status'].lower() == 'replay':
                name += ' ' + _.REPLAY_EVENT
            options.append(name)
            values.append(stream)

    if len(values) == 1:
        return values[0]

    index = gui.context_menu(options)
    if index < 0:
        return

    return values[index]

