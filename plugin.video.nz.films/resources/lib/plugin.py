from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.log import log

from .api import API
from .language import _

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder()

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.MY_LIBRARY, _bold=True), path=plugin.url_for(my_library))

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

    api.login(username=username, password=password)
    gui.refresh()

@plugin.route()
@plugin.login_required()
def my_library(**kwargs):
    folder = plugin.Folder(_.MY_LIBRARY)

    for row in api.my_library():
        item = plugin.Item(
            label = row['meta']['title'],
            path  = plugin.url_for(play, film_id=row['meta']['film_id']),
            art   = {'thumb': row['meta']['image_urls']['portrait']},
            info  = {'plot': row['meta']['overview'], 'mediatype': 'movie'},
            playable = True,
        )

        try:
            if row['meta']['trailers']:
                item.info['trailer'] = 'plugin://plugin.video.youtube/?action=play_video&videoid={}'.format(row['meta']['trailers'][0]['url'].split('?v=')[1])
        except:
            pass

        folder.add_items([item])

    return folder

@plugin.route()
@plugin.login_required()
def play(film_id, **kwargs):
    return api.get_stream(film_id)

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()