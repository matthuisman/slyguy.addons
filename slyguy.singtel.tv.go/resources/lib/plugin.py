import codecs

from slyguy import plugin, gui, signals, inputstream, settings

from .api import API
from .constants import *
from .language import _

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
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        folder.add_item(
            label    = str(row['chanelNumber']) + ' | ' + row['name'],
            art      = {'thumb': row['channelIcon']},
            path     = plugin.url_for(play, channel_id=row['id'], call_letter=row['shortName'], _is_live=True),
            playable = True
        )

    return folder

@plugin.route()
def login(**kwargs):
    singtel_tv_no = gui.input(_.SINGTEL_TV_NO).strip()
    if not singtel_tv_no:
        return

    identification_no = gui.input(_.IDENTIFICATION_NO).strip()
    if not identification_no:
        return

    api.login(singtel_tv_no, identification_no)
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.login_required()
def play(channel_id, call_letter, **kwargs):
    data = api.play(channel_id, call_letter)

    item = plugin.Item(
        path        = data['url'],
        headers     = {'X-AxDRM-Message': data['DRMToken']},
        inputstream = inputstream.Widevine(
            license_key  = '{}?KID={}'.format(data['LicenseURL'], data['KeyID']),
        ),
    )

    return item

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in api.channels():
            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" tvg-logo="{logo}" group-title="{group}",{name}\n{path}\n'.format(
                        id=row['id'], channel=row['chanelNumber'], name=row['name'], logo=row['channelIcon'], group=row['channelGenre'],
                        path=plugin.url_for(play, channel_id=row['id'], call_letter=row['shortName'], _is_live=True)))