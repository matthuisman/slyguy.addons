import codecs

import arrow

from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.exceptions import PluginError

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
    folder = plugin.Folder()

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live))
        folder.add_item(label=_(_.REPLAY, _bold=True), path=plugin.url_for(replay))
        folder.add_item(label=_(_.HIGHLIGHTS, _bold=True), path=plugin.url_for(highlights))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.channels():
        folder.add_item(
            label = row['name'],
            art = {'thumb': THUMB_URL.format('channels/{id}_landscape.png'.format(id=row['id']))},
            playable = True,
            path = plugin.url_for(play,  media_id=row['id'], media_type=MEDIA_CHANNEL, _is_live=True),
        )

    return folder

@plugin.route()
def replay(**kwargs):
    folder = plugin.Folder(_.REPLAY)

    now = arrow.utcnow()
    earliest = now.shift(hours=-24)

    dates = [now, earliest]
    for date in dates:
        for row in reversed(api.schedule(date)):
            if row['start'] < earliest or row['start'] > now or row['stop'] > now:
                continue

            icon = THUMB_URL.format('channels/{id}_landscape.png'.format(id=row['channel']))

            item = plugin.Item(
                label = u'{}: {}'.format(row['start'].to('local').humanize(), row['title']),
                info = {'plot': row['desc'], 'duration': row['duration']},
                art = {'thumb': icon},
                path = plugin.url_for(play, media_id=row['channel'], media_type=MEDIA_CHANNEL, start=row['start'].timestamp, duration=row['duration']),
                playable = True,
            )

            folder.add_items(item)

    return folder

@plugin.route()
def highlights(page=1, **kwargs):
    page = int(page)
    folder = plugin.Folder(_.HIGHLIGHTS)

    data = api.highlights(page=page)
    total_pages = int(data['paging']['totalPages'])

    if total_pages > 1:
        folder.title += _(_.PAGE_TITLE, cur_page=page, total_pages=total_pages)

    for row in data['programs']:
        try:
            split = row['runtimeMins'].split(':')
            duration = int(split[0]) * 60
            if len(split) > 1:
                duration += int(split[1])
        except:
            duration = 0

        folder.add_item(
            label = row['name'],
            info = {'plot': row.get('description'), 'duration': duration},
            art = {'thumb': THUMB_URL.format(row.get('image', ''))},
            playable = True,
            path = plugin.url_for(play, media_id=row['id'], media_type=MEDIA_VIDEO),
        )

    if page < total_pages:
        folder.add_item(
            label = _(_.NEXT_PAGE, next_page=page+1),
            path  = plugin.url_for(highlights, page=page+1),
        )

    return folder

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
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
@plugin.login_required()
def play(media_id, media_type, start=None, duration=None, **kwargs):
    if start:
        start = int(start)
        now = arrow.utcnow()
        if start > now.timestamp:
            raise PluginError(_.NOT_STARTED_YET)
        elif start < now.shift(hours=-24).timestamp:
            raise PluginError(_.EVENT_EXPIRED)

    data = api.play(media_id, media_type, start, duration)

    headers = HEADERS
    headers.update({'Authorization': 'bearer {}'.format(data['drmToken'])})

    item = plugin.Item(
        path        = data['path'],
        inputstream = inputstream.Widevine(license_key=WIDEVINE_URL),
        headers     = headers,
    )

    if media_type == MEDIA_CHANNEL:
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(EPG_URL))

        for row in api.channels():
            thumb = THUMB_URL.format('channels/{id}_landscape.png'.format(id=row['id']))

            catchup = plugin.url_for(play, media_id=row['id'], media_type=MEDIA_CHANNEL, start='{utc}', duration='{duration}')
            catchup = catchup.replace('%7Butc%7D', '{utc}').replace('%7Bduration%7D', '{duration}')

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-logo="{logo}" catchup="default" catchup-days="1" catchup-source="{catchup}",{name}\n{url}'.format(
                id=row['id'], logo=thumb, name=row['name'], url=plugin.url_for(play, media_id=row['id'], media_type=MEDIA_CHANNEL, _is_live=True), catchup=catchup))
