import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor

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
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login))
    else:
        folder.add_item(label=_(_.LIVE, _bold=True),  path=plugin.url_for(live))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE)

    now = arrow.now()
    entitlements = api.entitlements()
    for panel in api.live():
        current = None
        for epg in panel.get('items', {}).get('member', []):
            epg['startDate'] = arrow.get(epg['startDate'])
            epg['endDate'] = arrow.get(epg['endDate'])

            if epg.get('isLiveNow') and (not current or epg['startDate'] < now):
                current = epg

        if not current or not current.get('callSign'):
            continue

        sku = current['contentSKUResolved'][0]['baseId'].split('.')[-1]
        if sku not in entitlements:
            continue

        plot = u''
        epg_count = 6
        for epg in panel.get('items', {}).get('member', []):
            if epg['startDate'] >= current['startDate']:
                title = epg['seriesName']
                if epg['headline'].lower() != epg['seriesName'].lower():
                    title += u' - {}'.format(epg['headline'])

                plot += u'[{}] {}\n'.format(epg['startDate'].to('local').format('h:mma'), title)
                epg_count -= 1
                if not epg_count:
                    break

        title = current['seriesName']
        if current['headline'].lower() != current['seriesName'].lower():
            title += u' - {}'.format(current['headline'])
        title += u' [{}]'.format(current['callSign'])

        folder.add_item(
            label = title,
            info = {
                'plot': plot,
            },
            art = {
                'thumb': current['images']['seriesList']['HD'],
               # 'fanart': NETWORK_LOGO.format(network=current['network']),
            },
            playable = True,
            path = plugin.url_for(play_channel, callsign=current['callSign'], _is_live=True),
        )

    return folder

@plugin.route()
def login(**kwargs):
    data = api.provider_login()
    with gui.progress(_(_.LOGIN_STEPS, code=data['code'], url=data['url']), heading=_.PROVIDER_LOGIN) as progress:
        for i in range(data['timeout']):
            if progress.iscanceled() or monitor.waitForAbort(1):
                break

            progress.update(int((i / float(data['timeout'])) * 100))

            if i % 5 == 0 and api.check_auth(data['device_id']):
                gui.refresh()
                return

@plugin.route()
@plugin.login_required()
def play_channel(callsign, **kwargs):
    def get_stream_id():
        for panel in api.live():
            if panel.get('callSign') != callsign:
                continue

            current = None
            for epg in panel.get('items', {}).get('member', []):
                epg['startDate'] = arrow.get(epg['startDate'])
                if epg.get('isLiveNow') and (not current or epg['startDate'] > current['startDate']):
                    current = epg

            return current['id']

    stream_id = get_stream_id()
    if not stream_id:
        raise PluginError(_.NO_STREAM_ID)

    url = api.play(stream_id, stream_type='live')

    return plugin.Item(
        path = url,
        inputstream = inputstream.HLS(live=True),
    )

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()
