import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_TAG, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START

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
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(page, slug='/', label=_.FEATURED))
        folder.add_item(label=_(_.LIVE, _bold=True), path=plugin.url_for(page, slug='/live'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def page(slug, label=None, module_id=None, **kwargs):
    data = api.page(slug)

    folder = plugin.Folder(label or data['title'].replace('Page','').strip())

    for module in data['modules']:
        if module_id:
            if module['id'] == module_id:
                items = _process_rows(module.get('contentData') or [])
                folder.add_items(items)
        else:
            if module['moduleType'] == 'CuratedTrayModule':
                items = _process_rows(module.get('contentData') or [])
                folder.add_items(items)
            elif module['moduleType'] == 'GeneratedTrayModule':
                folder.add_item(
                    label = module['title'],
                    path = plugin.url_for(page, slug=slug, label=module['title'], module_id=module['id']),
                )

    return folder

def _process_rows(rows):
    items = []

    now = arrow.now()
    for row in rows:
        gist = row['gist']

        if gist['isVisible'] and gist['contentType'] in ('VIDEO',):
            label = gist['title']
            is_live = gist['isLiveStream']

            #gist['skipRecapEndTime']
            #gist['skipIntroEndTime']

            start = arrow.get(gist['scheduleStartDate']/1000) if gist['scheduleStartDate'] else None
            if start and start > now:
                label += ' [B][{}][/B]'.format(start.to('local').format('h:mma Do MMM YYYY'))
                is_live = False

            elif is_live:
                label += ' [B][LIVE][/B]'

            item = plugin.Item(
                label = label,
                art = {'thumb': gist['videoImageUrl']},
                info = {'plot': gist['description'], 'duration': gist['runtime']},
                path = plugin.url_for(play, video_id=gist['id'], _is_live=is_live),
                playable = True,
            )

            # if is_live:
            #     item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
            #         plugin.url_for(play, video_id=gist['id'], play_type=PLAY_FROM_LIVE, _is_live=True)
            #     )))

            #     item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
            #         plugin.url_for(play, video_id=gist['id'], play_type=PLAY_FROM_START, _is_live=True)
            #     )))

            items.append(item)

    return items

@plugin.route()
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    rows = api.search(query)
    items = _process_rows(rows)
    folder.add_items(items)

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
@plugin.login_required()
def play(video_id, play_type=None, **kwargs):
    url = api.play(video_id)
    play_type = int(play_type) if play_type else settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)
    is_live = ROUTE_LIVE_TAG in kwargs

    item = plugin.Item(
        path = url,
        inputstream = inputstream.HLS(live=is_live),
    )

    # if is_live and (play_type == PLAY_FROM_START or (play_type == PLAY_FROM_ASK and not gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START))):
    #     item.properties['ResumeTime'] = '1'
    #     item.properties['TotalTime']  = '1'
    #     item.inputstream.force = True

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()