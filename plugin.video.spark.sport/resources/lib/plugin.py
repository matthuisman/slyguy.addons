import codecs

import arrow

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.constants import PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_LIVE_TAG

from .api import API
from .language import _
from .constants import IMG_URL

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
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))
        folder.add_item(label=_(_.WHATS_ON, _bold=True), path=plugin.url_for(whats_on))
        folder.add_item(label=_(_.SPORTS,   _bold=True), path=plugin.url_for(sports))
        folder.add_item(label=_(_.CHANNELS, _bold=True), path=plugin.url_for(channels))
        folder.add_item(label=_(_.FREEMIUM, _bold=True), path=plugin.url_for(page, page_id='FREEMIUM'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def featured(**kwargs):
    folder = plugin.Folder(_.FEATURED)
    folder.add_items(_page('HOME')['items'])
    return folder

@plugin.route()
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    # rows = api.whats_on(query)
    # items = _process_rows(rows)

    rows = api.search(query)
    folder.add_items(_process_rows(rows))

    return folder

@plugin.route()
def sports(**kwargs):
    folder = plugin.Folder(_.SPORTS)

    info = api.sparksport()

    for row in info['sports']:
        page_info = info['pageInformation'].get(row['id'])
        if not page_info or row['isHidden']:
            continue

        folder.add_item(
            label = row['name'],
            art   = {'thumb': IMG_URL.format(row['images']['channelLogo'])},
            path  = plugin.url_for(page, page_id=page_info['RAILS_V3_PAGE_ID']),
        )

    return folder

@plugin.route()
def whats_on(**kwargs):
    folder = plugin.Folder(_.WHATS_ON)
    rows = api.whats_on()
    folder.add_items(_process_rows(rows))
    return folder

def _process_rows(rows):
    items  = []
    alerts = userdata.get('alerts', [])
    now    = arrow.utcnow()

    for row in rows:
        try:
            thumb = IMG_URL.format(row.get('pictureID') or row['pictures']['16x9'])
        except:
            thumb = None

        description = row.get('shortDescription') or None

        start_time = arrow.get(row.get('startTime') or None)
        end_time   = arrow.get(row.get('endTime') or None)
        now        = arrow.utcnow()

        item = plugin.Item(
            label     = row['name'],
            info      = {'plot': description},
            art       = {'thumb': thumb},
            path      = plugin.url_for(play, id=row['id']),
            playable  = True,
            is_folder = False,
        )

        if row.get('resourceType') == 'epg/stations':
            item.path = plugin.url_for(play, id=row['id'], _is_live=True)

        elif start_time < now and end_time > now:
            item.label += _(_.LIVE, _bold=True)

            if row.get('customAttributes', {}).get('isLinearChannelInLiveEvent') != 'true':
                item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
                    plugin.url_for(play, id=row['id'], play_type=PLAY_FROM_LIVE, _is_live=True)
                )))

                item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
                    plugin.url_for(play, id=row['id'], play_type=PLAY_FROM_START, _is_live=True)
                )))

            item.path = plugin.url_for(play, id=row['id'], play_type=settings.getEnum('live_play_type', PLAY_FROM_TYPES, PLAY_FROM_ASK), _is_live=True)

        elif start_time > now.shift(seconds=10):
            item.label += start_time.to('local').format(_.DATE_FORMAT)
            item.path = plugin.url_for(alert, asset=row['id'], title=row['name'])
            item.playable = False

            if row['id'] not in alerts:
                item.info['playcount'] = 0
            else:
                item.info['playcount'] = 1

        items.append(item)

    return items

def _page(page_id):
    items = []

    page_data = api.page(page_id)
    for row in page_data['sections']:
        #flatten
        if len(page_data['sections']) == 1 and row.get('title') and row.get('items'):
            return {'title': row['title'], 'items': _process_rows(row['items'])}

        data = api.section(row['id'])
        if not data.get('items'):
            continue

        item = plugin.Item(
            label = data['title'],
            path = plugin.url_for(section, section_id=row['id']),
        )

        items.append(item)

    return {'title':page_data['title'], 'items':items}

@plugin.route()
def alert(asset, title, **kwargs):
    alerts = userdata.get('alerts', [])

    if asset not in alerts:
        alerts.append(asset)
        gui.notification(title, heading=_.REMINDER_SET)
    else:
        alerts.remove(asset)
        gui.notification(title, heading=_.REMINDER_REMOVED)

    userdata.set('alerts', alerts)
    gui.refresh()

@plugin.route()
def page(page_id, **kwargs):
    data = _page(page_id)

    folder = plugin.Folder(data['title'])
    folder.add_items(data['items'])

    return folder

@plugin.route()
def section(section_id, **kwargs):
    data = api.section(section_id)
    folder = plugin.Folder(data['title'])
    folder.add_items(_process_rows(data['items']))
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
def play(id, play_type=PLAY_FROM_LIVE, **kwargs):
    mpd_url, license, headers, from_start = api.play(id)

    item = plugin.Item(
        path        = mpd_url,
        inputstream = inputstream.Widevine(license_key=license),
        headers     = headers,
        use_proxy   = True, #needed for live with multiple periods and fix https://github.com/xbmc/inputstream.adaptive/pull/668
    )

    play_type = int(play_type)
    if from_start and (play_type == PLAY_FROM_START or (play_type == PLAY_FROM_ASK and not gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START))):
        item.properties['ResumeTime'] = 1
        item.properties['TotalTime']  = 1

    return item

@plugin.route()
def channels(**kwargs):
    folder = plugin.Folder(_.CHANNELS)

    rows = api.live_channels()
    folder.add_items(_process_rows(rows))

    return folder

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@signals.on(signals.ON_SERVICE)
def service():
    api.refresh_token()
    alerts = userdata.get('alerts', [])
    if not alerts:
        return

    now     = arrow.now()
    notify  = []
    _alerts = []

    for id in alerts:
        entity = api.entitiy(id)
        if not entity:
            continue

        start = arrow.get(entity.get('startTime'))

        if now > start and (now - start).total_seconds() <= 60*10:
            notify.append(entity)
        elif now < start:
            _alerts.append(id)

    userdata.set('alerts', _alerts)

    for entity in notify:
        if not gui.yes_no(_(_.EVENT_STARTED, event=entity['name']), yeslabel=_.WATCH, nolabel=_.CLOSE):
            continue

        with signals.throwable():
            play(id=entity['id'], play_type=settings.getEnum('live_play_type', LIVE_PLAY_TYPES, default=FROM_CHOOSE))

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    channels = api.live_channels()

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for channel in channels:
            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                id=channel['id'], name=channel['name'], logo=IMG_URL.format(channel['pictureID']),
                    path=plugin.url_for(play, id=channel['id'], _is_live=True)))