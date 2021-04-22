import arrow

from slyguy import settings, plugin, database, cache, gui, userdata, inputstream, util, signals
from slyguy.exceptions import PluginError
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START

from .constants import SERVICE_TIME, GAMES_EXPIRY, GAMES_CACHE_KEY, IMG_URL
from .api import API
from .models import Game, Alert
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
        folder.add_item(label=_(_.LIVE, _bold=True), path=plugin.url_for(live), cache_key=GAMES_CACHE_KEY)
        folder.add_item(label=_(_.PLAYED, _bold=True), path=plugin.url_for(played), cache_key=GAMES_CACHE_KEY)
        folder.add_item(label=_(_.UPCOMING, _bold=True), path=plugin.url_for(upcoming), cache_key=GAMES_CACHE_KEY)

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

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
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
def live(**kwargs):
    return show_games(Game.state == Game.LIVE, title=_.LIVE)

@plugin.route()
def played(**kwargs):
    return show_games(Game.state << (Game.PROCESSING, Game.PLAYED), title=_.PLAYED)

@plugin.route()
def upcoming(**kwargs):
    return show_games(Game.state == Game.UPCOMING, order_by=Game.start.asc(), title=_.UPCOMING)

@plugin.route()
def alerts(slug, **kwargs):
    game   = get_game(slug)
    alerts = userdata.get('alerts', [])

    if game.id not in alerts:
        alerts.append(game.id)
        gui.notification(_.REMINDER_SET, heading=game.title, icon=game.image)
    else:
        alerts.remove(game.id)
        gui.notification(_.REMINDER_REMOVED, heading=game.title, icon=game.image)

    userdata.set('alerts', alerts)
    gui.refresh()

@plugin.route()
def show_score(slug, **kwargs):
    game = get_game(slug)
    gui.ok(heading=game.title, message=game.result)

@plugin.route()
def play(slug, game_type, play_type=PLAY_FROM_LIVE, **kwargs):
    game = get_game(slug)
    return _get_play_item(game, game_type, play_type)

@plugin.login_required()
def _get_play_item(game, game_type, play_type=PLAY_FROM_LIVE):
    play_type = int(play_type)
    item      = parse_game(game)
    is_live   = game.state == Game.LIVE

    item.inputstream = inputstream.HLS(live=is_live)

    if play_type == PLAY_FROM_START or (play_type == PLAY_FROM_ASK and not gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START)):
        item.properties['ResumeTime'] = '1'
        item.properties['TotalTime']  = '1'
        if is_live and not item.inputstream.check():
            raise PluginError(_.HLS_REQUIRED)

    item.path = api.get_play_url(game, game_type)

    return item

@signals.on(signals.ON_SERVICE)
def service():
    update_games()
    check_alerts()

def show_games(query, order_by=None, title=None):
    folder = plugin.Folder(title, no_items_label=_.NO_GAMES)

    if not order_by:
        order_by = Game.start.desc()

    if not cache.get(GAMES_CACHE_KEY):
        update_games()

    games = Game.select().where(query).order_by(order_by)
    items = [parse_game(game) for game in games]
    folder.add_items(items)

    return folder

def update_games():
    api.update_games()
    cache.set(GAMES_CACHE_KEY, True, expires=GAMES_EXPIRY)

def get_game(slug):
    game = Game.get_or_none(Game.slug == slug)
    if not game:
        try:
            game = api.fetch_game(slug)
            game.save()
        except:
            raise PluginError(_.ERROR_GAME_NOT_FOUND)

    return game

def parse_game(game):
    item = plugin.Item(
        label     = game.title,
        is_folder = False,
        playable  = game.state != Game.UPCOMING,
        art       = {'thumb': game.image},
        info      = {
            'title':    game.title,
            'plot':     game.description,
            'duration': game.duration,
            'aired':    game.aired,
        },
    )

    if game.state == Game.UPCOMING:
        item.path = plugin.url_for(alerts, slug=game.slug)

        if game.id not in userdata.get('alerts', []):
            item.info['playcount'] = 0
            item.context.append((_.SET_REMINDER, "RunPlugin({0})".format(item.path)))
        else:
            item.info['playcount'] = 1
            item.context.append((_.REMOVE_REMINDER, "RunPlugin({0})".format(item.path)))

    elif game.state == Game.LIVE:
        item.path = plugin.url_for(play, slug=game.slug, game_type=Game.FULL, play_type=settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK), _is_live=True)

        item.context.append((_.WATCH_LIVE, "PlayMedia({0})".format(
            plugin.url_for(play, slug=game.slug, game_type=Game.FULL, play_type=PLAY_FROM_LIVE, _is_live=True)
        )))

        item.context.append((_.WATCH_FROM_START, "PlayMedia({0})".format(
            plugin.url_for(play, slug=game.slug, game_type=Game.FULL, play_type=PLAY_FROM_START, _is_live=True)
        )))

    elif game.state == Game.PROCESSING:
        item.path = plugin.url_for(play, slug=game.slug, game_type=Game.FULL)
        item.context.append((_.FULL_GAME, "PlayMedia({0})".format(item.path)))

    elif game.state == Game.PLAYED:
        item.path = plugin.url_for(play, slug=game.slug, game_type=Game.FULL)
        item.context.append((_.FULL_GAME, "PlayMedia({0})".format(item.path)))
        item.context.append((_.CONDENSED_GAME, "PlayMedia({0})".format(
            plugin.url_for(play, slug=game.slug, game_type=Game.CONDENSED)
        )))

    if game.result:
        item.context.append((_.SHOW_SCORE, "RunPlugin({0})".format(
            plugin.url_for(show_score, slug=game.slug)
        )))

    return item

def check_alerts():
    alerts = userdata.get('alerts', [])
    if not alerts: return

    for game in Game.select().where(Game.id << alerts):
        if game.state == Game.LIVE:
            alerts.remove(game.id)

            _to_start = game.start - arrow.utcnow().timestamp

            if settings.getInt('alert_when') == Alert.STREAM_START:
                message = _.STREAM_STARTED
            elif settings.getInt('alert_when') == Alert.KICK_OFF and _to_start > 0 and _to_start <= SERVICE_TIME:
                message = _.KICKOFF
            else:
                continue

            if settings.getInt('alert_type') == Alert.NOTIFICATION:
                gui.notification(message, heading=game.title, time=5000, icon=game.image)

            elif gui.yes_no(message, heading=game.title, yeslabel=_.WATCH, nolabel=_.CLOSE):
                _get_play_item(game, Game.FULL, play_type=settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)).play()

        elif game.state != Game.UPCOMING:
            alerts.remove(game.id)

    userdata.set('alerts', alerts)