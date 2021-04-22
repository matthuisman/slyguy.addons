import codecs

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.exceptions import Error
from slyguy.constants import ROUTE_LIVE_TAG

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
        folder.add_item(label=_(_.LIVE_TV, _bold=True),  path=plugin.url_for(live_tv))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

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

    api.login(username, password)
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        folder.add_item(
            label = row['title'],
            art = {'thumb': row['tileImage']['uri']},
            playable = True,
            path = plugin.url_for(play_channel, id=row['id'], _is_live=True),
        )

    return folder

@plugin.route()
@plugin.login_required()
def play_channel(id, **kwargs):
    url, license = api.play_channel(id)

    item = plugin.Item(
        path        = url,
        headers     = HEADERS,
        inputstream = inputstream.Widevine(
            license_key = license,
        ),
    )

    if kwargs.get(ROUTE_LIVE_TAG):
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in api.channels():
            f.write(u'#EXTINF:-1 tvg-id="sky.{id}" tvg-chno="{channel}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                        id=row['number'], channel=row['number'], name=row['title'], logo=row['tileImage']['uri'],
                            path=plugin.url_for(play_channel, id=row['id'], _is_live=True)))