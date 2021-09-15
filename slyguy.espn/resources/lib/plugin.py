import arrow
from slyguy import plugin, gui, signals, inputstream, settings, userdata
from slyguy.log import log
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor
from slyguy.constants import ROUTE_LIVE_TAG
from slyguy.exceptions import PluginError

from .constants import *
from .language import _
from .api import API

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

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.ACCOUNT, path=plugin.url_for(account), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE)

    avail_auth = []
    if api.provider.logged_in:
        avail_auth.append('mvpd')
    if api.espn.logged_in:
        avail_auth.append('direct')

    hidden = userdata.get('hidden', [])

    data = api.bucket(LIVE_BUCKET_ID)
    events = []
    for row in data['buckets'][0]['contents']:
        if row['status'] != 'live' and not settings.getBool('show_upcoming', False):
            continue

        streams = []
        for stream in row['streams']:
            if stream['source']['id'] in hidden:
                continue

            if any(x in stream['authTypes'] for x in avail_auth):
                streams.append(stream)

        if not streams:
            continue

        if row.get('eventId'):
            if row['eventId'] in events:
                continue
            events.append(row['eventId'])
            path = plugin.url_for(play, event_id=row['eventId'], _is_live=True)
        else:
            path = plugin.url_for(play, content_id=row['id'], _is_live=True)

        sources = u'/'.join([x['source']['name'] for x in streams])

        label = u'{name} [{sources}] '.format(name=row['name'], sources=sources)
        if row['status'] != 'live':
            label = u'{} [{}]'.format(label, arrow.get(row['utc']).to('local').format('h:mm A'))

        folder.add_item(
            label = label,
            info = {
                'plot': row['subtitle'],
            },
            art = {'thumb': row['imageHref']},
            playable = True,
            path = path,
            context = ((_.HIDE_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(hide_channel, id=streams[0]['source']['id']))),),
        )

    return folder

@plugin.route()
def hide_channel(id, **kwargs):
    hidden = userdata.get('hidden', [])
    if id not in hidden:
        hidden.append(id)
    userdata.set('hidden', hidden)
    gui.refresh()

@plugin.route()
def clear_hidden(**kwargs):
    userdata.delete('hidden')
    gui.notification(_.RESET_HIDDEN_OK)

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
        with gui.progress(_(_.LOGIN_STEPS, code=login_progress.code), heading=_.ESPN_LOGIN) as progress:
            for i in range(timeout):
                if progress.iscanceled() or not login_progress.is_alive() or monitor.waitForAbort(1):
                    break

                progress.update(int((i / float(timeout)) * 100))

            login_progress.stop()
            return login_progress.result

def _provider_login(**kwargs):
    with api.provider.login() as data:
        with gui.progress(_(_.LOGIN_STEPS, code=data['code']), heading=_.PROVIDER_LOGIN) as progress:
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
        content_id = _select_stream(event_id)
        if not content_id:
            return

    elif network_id:
        data = api.play_network(network_id)
        content_id = data['id']

    playback_data = api.play(content_id)

    return plugin.Item(
        path = playback_data['url'],
        inputstream = inputstream.HLS(live=is_live),
        headers = playback_data.get('headers'),
    )

def _select_stream(event_id):
    options = []
    values = []

    avail_auth = []
    if api.provider.logged_in:
        avail_auth.append('mvpd')
    if api.espn.logged_in:
        avail_auth.append('direct')

    hidden = userdata.get('hidden', [])

    for group in api.picker(event_id):
        for row in group.get('contents', []):
            if row.get('status') != 'live' or not row.get('streams'):
                continue

            stream = row['streams'][0]
            if stream['source']['id'] in hidden:
                continue
            if not any(x in stream['authTypes'] for x in avail_auth):
                continue

            options.append(row['name'])
            values.append(row['id'])

    if not values:
        raise PluginError(_.NO_SOURCE)

    elif len(values) == 1:
        return values[0]

    index = gui.select(options=options, heading=_.SELECT_BROADCAST)
    if index < 0:
        return

    return values[index]
