import arrow

from slyguy import plugin, gui, userdata, signals, settings
from slyguy.constants import ROUTE_LIVE_TAG

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
def races(year=None, **kwargs):
    if year is None:
        folder = plugin.Folder(_.RACES)

        row = api.live()
        row['name'] += ' [LIVE]'
        row['is_live'] = True
        folder.add_items(process_rows([row]))

        for i in range(arrow.now().year, 2019-1, -1):
            folder.add_item(
                label = str(i),
                path = plugin.url_for(races, year=i)
            )

        return folder

    folder = plugin.Folder(year, no_items_label=_.NO_RACES)
    rows = api.races(year=int(year))
    folder.add_items(process_rows(rows))
    return folder

def process_rows(rows):
    items = []
    for row in rows:
        if not row['duration'] and not row.get('is_live'):
            continue

        item = plugin.Item(
            label = row['name'],
            art = {'thumb': row.get('poster')},
            playable = True,
            path = plugin.url_for(play, id=row['id'], _is_live=row.get('is_live', False)),
            info = {
                'plot': row.get('long_description'),
                'aired': row['published_at'] if not row.get('is_live') else None,
                'duration': (row['duration'] / 1000) if not row.get('is_live') else None,
            },
        )
        items.append(item)

    return items

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
