from slyguy import plugin, gui, userdata, signals, settings
from slyguy.exceptions import Error
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_LIVE_TAG

from .api import API
from .language import _

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not plugin.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.RACES, _bold=True), path=plugin.url_for(races))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), bookmark=False)
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
@plugin.login_required()
def races(**kwargs):
    folder = plugin.Folder(_.RACES, no_items_label=_.NO_RACES)

    rows = [api.live()]
    rows.extend(api.races())
    for row in rows:
        folder.add_item(
            label = row['name'],
            art = {'thumb': row['poster']},
            playable = True,
            path = plugin.url_for(play, id=row['id'], _is_live=row['duration'] < 0)
        )

    return folder

@plugin.route()
@plugin.login_required()
def play(id, **kwargs):
    item = api.play(id)

    if ROUTE_LIVE_TAG in kwargs and item.inputstream:
        item.inputstream.live = True

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()
