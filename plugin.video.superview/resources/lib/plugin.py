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
@plugin.login_required()
def races(**kwargs):
    folder = plugin.Folder(_.RACES, no_items_label=_.NO_RACES)

    races = api.races()

    for slug in races:
        folder.add_item(
            label = races[slug]['title'],
            path  = plugin.url_for(race, slug=slug)
        )

    return folder

@plugin.route()
@plugin.login_required()
def race(slug, **kwargs):
    races = api.races()
    if slug not in races:
        raise Error(_.RACE_NOT_FOUND)

    race = races[slug]
    folder = plugin.Folder(race['title'], no_items_label=_.NO_STREAMS)

    for stream in race['streams']:
        if not stream['slug']:
            continue

        item = plugin.Item(
            label = stream['label'],
            path  = plugin.url_for(play, slug=stream['slug']),
            playable = True,
        )

        if stream['live']:
            item.label = _(_.LIVE_LABEL, title=stream['label'])

            item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
                plugin.url_for(play, slug=stream['slug'], play_type=PLAY_FROM_LIVE, _is_live=True)
            )))

            item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
                plugin.url_for(play, slug=stream['slug'], play_type=PLAY_FROM_START, _is_live=True)
            )))

            item.path = plugin.url_for(play, slug=stream['slug'], play_type=settings.getEnum('live_play_type', PLAY_FROM_TYPES, PLAY_FROM_ASK), _is_live=True)

        folder.add_items([item])

    return folder

@plugin.route()
@plugin.login_required()
def play(slug, play_type=PLAY_FROM_LIVE, **kwargs):
    item = api.play(slug)

    if ROUTE_LIVE_TAG in kwargs and item.inputstream:
        item.inputstream.live = True

    play_type = int(play_type)
    if play_type == PLAY_FROM_LIVE or (play_type == PLAY_FROM_ASK and not gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START)):
        item.properties['ResumeTime'] = 1
        item.properties['TotalTime']  = 1

    return item

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
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()