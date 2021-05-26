import codecs

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.exceptions import Error
from slyguy.constants import ROUTE_LIVE_TAG
from slyguy.util import pthms_to_seconds

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
        folder.add_item(label=_(_.MOVIES, _bold=True),  path=plugin.url_for(collection, id=MOVIES_ID))

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
def collection(id, filters=None, page=1, after=None, **kwargs):
    page = int(page)
    data = api.collection(id, filters, after=after, tv_upcoming=False)
    folder = plugin.Folder(data['title'])

    if filters is None:
        folder.add_item(
            label = _(_.ALL, _bold=True),
            path = plugin.url_for(collection, id=id, filters=""),
        )

        for row in data.get('namedFilters', []):
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(collection, id=id, filters=row['id']),
            )

        return folder

    items = process_rows(data['contentPage']['content'])
    folder.add_items(items)

    if data['contentPage']['pageInfo']['hasNextPage']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path = plugin.url_for(collection, id=id, filters=filters, page=page+1, after=data['contentPage']['pageInfo']['endCursor']),
            specialsort = 'bottom',
        )

    return folder

def process_rows(rows):
    items = []

    for row in rows:
        if row['__typename'] == 'Movie':
            item = plugin.Item(
                label = row['title'],
                info = {
                    'duration': pthms_to_seconds(row['duration']),
                    'plot': row['synopsis'],
                    'year': row['year'],
                    'mediatype': 'movie',
                },
                art = {'thumb': row['contentTileHorizontal']['uri'] + '?impolicy=contentTileHorizontal', 'fanart': row['heroLandingWide']['uri']+ '?impolicy=heroLandingWide'},
            )

            if row['asset']:
                item.playable = True
                item.path = plugin.url_for(play, asset_id=row['asset']['id'])
            else:
                item.label = item.label + ' [B][Coming Soon][/B]'
                #item.path = plugin.url_for(reminder, id=row['id'])

            items.append(item)

    return items

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        folder.add_item(
            label = row['title'],
            art = {'thumb': row['tileImage']['uri']},
            playable = True,
            path = plugin.url_for(play, asset_id=row['id'], _is_live=True),
        )

    return folder

@plugin.route()
@plugin.login_required()
def play(asset_id, **kwargs):
    url, license = api.play(asset_id)

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
                            path=plugin.url_for(play, asset_id=row['id'], _is_live=True)))