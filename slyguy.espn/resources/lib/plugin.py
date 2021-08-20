import arrow
from slyguy import plugin, gui, signals, inputstream, settings
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

    data = api.bucket(LIVE_BUCKET_ID)
    for row in data['buckets'][0]['contents']:
        streams = []
        for stream in row['streams']:
            if any(x in stream['authTypes'] for x in avail_auth):
                streams.append(stream)

        if not streams:
            continue

        sources = u'/'.join([x['source']['name'] for x in streams])

        if len(streams) > 1:
            path = plugin.url_for(play, event_id=row['eventId'], _is_live=True)
        else:
            path = plugin.url_for(play, content_id=row['id'], _is_live=True)

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
        )

    return folder

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
        data = api.event(event_id)
        content_id = _select_stream(data)
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

def _select_stream(data):
    options = []
    values = []

    avail_auth = []
    if api.provider.logged_in:
        avail_auth.append('mvpd')
    if api.espn.logged_in:
        avail_auth.append('direct')

    for stream in data['streams']:
        if stream.get('status') != 'live':
            continue

        if any(x in stream['authTypes'] for x in avail_auth):
            options.append(stream['source']['name'])
            values.append(stream['id'])

    if not values:
        raise PluginError(_.NO_SOURCE)

    elif len(values) == 1:
        return values[0]

    index = gui.select(options=options, heading=_.SELECT_BROADCAST)
    if index < 0:
        return

    return values[index]
