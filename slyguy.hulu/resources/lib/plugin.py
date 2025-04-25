import re
import json
import codecs
from xml.sax.saxutils import escape

import arrow
from six.moves.urllib_parse import quote
from slyguy import plugin, gui, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor
from slyguy.log import log
from slyguy.constants import LIVE_HEAD, ROUTE_LIVE_TAG, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_RESUME_TAG, PLAY_FROM_TYPES, PLAY_FROM_ASK, NO_RESUME_TAG

from .api import API
from .language import _
from .settings import settings
from .constants import DEVICE_ACTIVATE_URL, HEADERS


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
        if not userdata.get('is_kids', False):
            if not settings.getBool('hide_live_channels', False):
                folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live))
            folder.add_item(label=_(_.HOME, _bold=True), path=_hub_path('home'))
            folder.add_item(label=_(_.TV, _bold=True), path=_hub_path('tv'))
            folder.add_item(label=_(_.MOVIES, _bold=True), path=_hub_path('movies'))
            folder.add_item(label=_(_.SPORTS, _bold=True), path=_hub_path('sports'))
            folder.add_item(label=_(_.HUBS, _bold=True), path=_hub_path('hubs'))

        if not settings.getBool('hide_kids', False) or userdata.get('is_kids', False):
            folder.add_item(label=_(_.KIDS, _bold=True), path=_hub_path('kids'))

        if not settings.getBool('hide_my_stuff', False):
            folder.add_item(label=_(_.MY_STUFF, _bold=True), path=_hub_path('watch-later', view=0))

        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _hub_path(slug, view=1):
    if slug.lower().startswith('https'):
        slug = '/'.join(slug.split('?')[0].split('/')[6:])
    return plugin.url_for(hub, slug=slug, view=view)

@plugin.route()
@plugin.pagination()
def hub(slug, view=1, page=1, **kwargs):
    data = api.hub(slug, page=page, view=bool(int(view)))
    folder = plugin.Folder(data.get('name'))

    if 'components' in data:
        for row in data['components']:
            if row['personalization']['bowie_context'] in ('recordings'):
                continue

            if row['_type'] == 'collection':
                if not row['items']:
                    continue

                folder.add_item(
                    label = row['name'],
                    path = _hub_path(row['href'], view=view),
                )

    elif 'items' in data:
        items = _process_rows(data['items'])
        folder.add_items(items)

    return folder, 'pagination' in data and data['pagination'].get('next')

def _process_rows(rows):
    my_stuff = not settings.getBool('hide_my_stuff', False)
    sync = settings.getBool('sync_playback', False)
    hide_locked = settings.getBool('hide_locked', True)
    hide_upcoming = settings.getBool('hide_upcoming', True)
    now = arrow.now().to('local')

    eab_ids = []
    to_process = []
    for row in rows:
        row['locked'] = False
        row['upcoming'] = False
        actions = row.get('actions', {})

        _type = row['metrics_info']['target_type'] if row['_type'] == 'view' else row['_type']

        if not row.get('browse') and 'browse' not in actions:
            continue

        if 'upsell' in actions:
            row['locked'] = True

        if 'bundle' not in row:
            try:
                row['bundle'] = row['reco_info']['watch_later_result']['actions'][0]['action_entity']['bundle']
            except:
                row['bundle'] = {}

        if hide_locked and row['locked']:
            continue

        row['id'] = row['metrics_info']['target_id'] if row['_type'] == 'view' else row['id']
        if _type in ('series', 'network', 'sports_team'):
            row['personalization']['eab'] = 'EAB::{}::NULL::NULL'.format(row['id'])
            eab_ids.append(row['personalization']['eab'])
            to_process.append(row)

        elif _type in ('movie', 'episode', 'sports_episode'):
            eab_ids.append(row['personalization']['eab'])
            to_process.append(row)

        else:
            log.debug('Unknown content type: {}'.format(_type))

    states = api.states(eab_ids)

    items = []
    for row in to_process:
        my_stuff_context = my_stuff
        state = states.get(row['personalization']['eab'], {})
        row['upcoming'] = state.get('is_upcoming', False)

        if row['upcoming'] and hide_upcoming:
            continue

        if row['_type'] == 'view':
            item = _parse_view(row, my_stuff, sync, state)
            items.append(item)
            continue

        if not row['upcoming'] and row['bundle'].get('bundle_type') == 'LIVE':
            continue

        label = row['name']
        if row['locked']:
            label = _(_.LOCKED, label=label)
        elif row['upcoming']:
            try:
                start_date = arrow.get(row['bundle']['availability']['start_date']).to('local')
                if start_date.format("DDDD") == now.format("DDDD"):
                    _str = ' [COLOR orange][{}][/COLOR]'
                    _format = 'h:mm A'
                else:
                    _str = ' [COLOR orange][{}][/COLOR]'
                    _format = 'MMM D, h:mm A'
                label += _str.format(start_date.format(_format))
            except:
                label = _(_.UPCOMING, label=label)

        premiere_date = row.get('premiere_date')
        try: premiere_date = arrow.get(premiere_date).to('local').format('YYYY-MM-DD')
        except: pass

        item = plugin.Item(
            label = label,
            info = {
                'plot': row.get('description'),
                'aired': premiere_date,
                'duration': row.get('duration'),
                'mpaa': row.get('rating', {}).get('code'),
                'genre': row.get('genre_names', []),
            },
            art = _entity_art(row['artwork']),
        )

        if row['_type'] in ('sports_team', 'network'):
            item.path = _hub_path(row['href'])

        elif row['_type'] in ('episode', 'sports_episode'):
            item.info.update({
                'season': int(row.get('season', 0)),
                'episode': int(row.get('number', 0)),
                'tvshowtitle': row.get('series_name'),
                'mediatype': 'episode',
            })
            item.playable = True
            item.path = _get_play_path(row['personalization']['eab'])
            my_stuff_context = False

        elif row['_type'] == 'series':
            item.info.update({
                'tvshowtitle': row['name'],
                'mediatype': 'tvshow',
            })
            item.path = plugin.url_for(series, id=row['id'])

        elif row['_type'] == 'movie':
            item.info.update({
                'mediatype': 'movie',
            })
            item.playable = True
            item.path = _get_play_path(row['personalization']['eab'])

        else:
            continue

        if my_stuff_context:
            item.context = [(_.REMOVE_MY_STUFF, 'RunPlugin({})'.format(plugin.url_for(remove_my_stuff, eab_id=row['personalization']['eab']))),] if state.get('is_bookmarked') else [(_.ADD_MY_STUFF, 'RunPlugin({})'.format(plugin.url_for(add_my_stuff, eab_id=row['personalization']['eab'], title=row['name']))),]

        if item.playable:
            item.info['playcount'] = 1 if sync and state.get('is_completed') else None
            item.resume_from = 1 if sync and state.get('progress_percentage') and not state.get('is_completed') else None

        items.append(item)

    return items

## USED IN SEARCH RESULTS & HUBS
def _parse_view(row, my_stuff, sync, state):
    metrics = row['metrics_info']
    entity = row['entity_metadata']

    try: bundle = row['actions']['playback']['bundle']
    except: bundle = {}
    try: row['name'] = row['visuals']['headline']['text']
    except: row['name'] = row['visuals']['headline']

    plot = None
    if 'body' in row['visuals']:
        try: plot = row['visuals']['body']['text']
        except: plot = row['visuals']['body']

    label = row['name'] = re.sub(" \(([0-9]{4})\)$", '', row['name'])
    if row['locked']:
        label = _(_.LOCKED, label=label)
    elif row['upcoming']:
        label = _(_.UPCOMING, label=label)
    elif bundle.get('bundle_type') == 'LIVE':
        label = _(_.LIVE, label=label)

    item = plugin.Item(
        label = label,
        info = {
            'plot': plot,
            'aired': entity.get('premiere_date'),
            'duration': bundle.get('duration'),
            'genre': entity.get('genre_names', []),
            'mpaa': entity.get('rating', {}).get('code'),
        },
        art = _view_art(row['visuals']['artwork']),
    )

    if metrics['target_type'] in ('sports_team', 'network'):
        item.path = _hub_path(row['actions']['browse']['href'])

    elif metrics['target_type'] == 'series':
        item.info.update({
            'tvshowtitle': row['name'],
            'mediatype': 'tvshow',
        })
        item.path = plugin.url_for(series, id=row['id'])

    elif metrics['target_type'] == 'movie':
        item.info.update({
            'mediatype': 'movie',
        })
        item.playable = True
        item.path = _get_play_path(row['personalization']['eab'])

    elif metrics['target_type'] in ('episode', 'sports_episode'):
        item.info.update({
            'season': int(row.get('season', 0)),
            'episode': int(row.get('number', 0)),
            'tvshowtitle': row.get('series_name'),
            'mediatype': 'episode',
        })
        item.playable = True
        item.path = _get_play_path(row['personalization']['eab'])
        my_stuff = False

    else:
        return None

    if not row['upcoming'] and bundle.get('bundle_type') == 'LIVE':
        item.info.pop('duration')
        item.path = _get_play_path(row['personalization']['eab'], play_type=None, _is_live=True)

        if settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK) != PLAY_FROM_ASK:
            item.context.append((_.PLAY_FROM_BEGINNING, "PlayMedia({})".format(
                _get_play_path(row['personalization']['eab'], play_type=PLAY_FROM_START, _is_live=True)
            )))

            item.context.append((_.PLAY_FROM_LIVE_CONTEXT, "PlayMedia({})".format(
                _get_play_path(row['personalization']['eab'], play_type=PLAY_FROM_LIVE, _is_live=True)
            )))

    if my_stuff:
        item.context = [(_.REMOVE_MY_STUFF, 'RunPlugin({})'.format(plugin.url_for(remove_my_stuff, eab_id=row['personalization']['eab']))),] if state.get('is_bookmarked') else [(_.ADD_MY_STUFF, 'RunPlugin({})'.format(plugin.url_for(add_my_stuff, eab_id=row['personalization']['eab'], title=row['name']))),]

    if item.playable:
        item.info['playcount'] = 1 if sync and state.get('is_completed') else None
        item.resume_from = 1 if sync and state.get('progress_percentage') and not state.get('is_completed') else None

    return item

@plugin.route()
def series(id, **kwargs):
    data = api.series(id)
    folder = plugin.Folder(data['details']['entity']['name'])

    series = []
    for row in data['components']:
        for item in row['items']:
            if 'series_grouping_metadata' in item:
                series.append(int(item['series_grouping_metadata']['season_number']))

    for season in sorted(series):
        folder.add_item(
            label = _(_.SEASON, number=season),
            info = {
                'plot': data['details']['entity']['description'],
                'mpaa': data['details']['entity']['rating'].get('code'),
                'tvshowtitle': data['details']['entity']['name'],
                'season': season,
                'mediatype': 'season',
            },
            art = _entity_art(data['details']['entity']['artwork']),
            path = plugin.url_for(episodes, id=id, season=season),
        )

    return folder

@plugin.route()
def remove_my_stuff(eab_id, **kwargs):
    api.remove_bookmark(eab_id)
    gui.refresh()

@plugin.route()
def add_my_stuff(eab_id, title, **kwargs):
    if api.add_bookmark(eab_id):
        gui.notification(_.ADDED_MY_STUFF, heading=title)
    gui.refresh()

def _entity_art(artwork):
    art = {'thumb': None, 'fanart': None}
    thumbs = ['program.vertical.tile', 'program.tile', 'title.treatment.horizontal', 'video.horizontal.hero', 'network.tile', 'team.tile']
    fanarts = ['detail.horizontal.wide', 'detail.horizontal.hero', 'network.tile', 'team.tile']

    for key in thumbs:
        if key in artwork:
            art['thumb'] = _image(artwork[key]['path'])
            break

    for key in fanarts:
        if key in artwork:
            art['fanart'] = _image(artwork[key]['path'], 'fanart')
            break

    return art

def _view_art(artwork):
    art = {'thumb': None, 'fanart': None}
    thumbs = ['vertical_tile', 'horizontal_tile', 'horizontal', 'horizontal_network']
    fanarts = ['horizontal', 'horizontal_video', 'horizontal_network']

    for key in thumbs:
        if key in artwork and artwork[key]['artwork_type'] == 'display_image':
            art['thumb'] = _image(artwork[key]['image']['path'])
            break

    for key in fanarts:
        if key in artwork and artwork[key]['artwork_type'] == 'display_image':
            art['fanart'] = _image(artwork[key]['image']['path'], 'fanart')
            break

    return art

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    rows = api.search(query)
    return _process_rows(rows), False

@plugin.route()
def episodes(id, season, **kwargs):
    data = api.episodes(id, season)

    if not data['items']:
        return plugin.Folder(data['name'])

    art = _entity_art(data['items'][0]['series_artwork'])
    folder = plugin.Folder(data['items'][0]['series_name'], fanart=art['fanart'])
    items = _process_rows(data['items'])
    folder.add_items(items)
    return folder

def _image(url, _type=None):
    if _type == 'live':
        operations = [{"trim":"(0,0,0,0)"},{"resize":"600x600|max"},{"extent":"600x600"},{"format":"png"}]
    elif _type == 'fanart':
        operations = [{"resize":"1920x1920|max"},{"format":"jpeg"}]
    else:
        operations = [{"resize":"600x600|max"},{"format":"jpeg"}]

    operations = json.dumps(operations)
    #auth = 'Bearer {}'.format(userdata.get('user_token'))
    #return 'https://img.hulu.com/user/v3/artwork/{}&operations={}|authorization={}'.format(url.split('/')[-1], quote(operations), quote(auth))
    cookie = '_hulu_at=eyJhbGciOiJSUzI1NiJ9.eyJhc3NpZ25tZW50cyI6ImV5SjJNU0k2VzExOSIsInJlZnJlc2hfaW50ZXJ2YWwiOjg2NDAwMDAwLCJ0b2tlbl9pZCI6ImIxMzJjY2FiLTNmMjQtNDQ1OS05MmY0LTA2NzBjMzI0NzdlZCIsImFub255bW91c19pZCI6ImJhMzUyYjEzLWFkNDEtNDhlNS04YjUyLTljMTA0N2IxMDIxNyIsImlzc3VlZF9hdCI6MTYzMTUwNjcwNTYwOCwidHRsIjozMTUzNjAwMDAwMCwiZGV2aWNlX3VwcGVyIjoxfQ.rzn7mJF2gsB-8nEi6TEUtWnt8bztjmP3vHGzo_XBa6yX1q8_sMJ8GoK0-_p5j8Rn65wZdaAYfTrK5TKg-e1upjZOwfOFNJucFZkJKLcn-ZtKoHDJoRi22RSnJMtHzKLfk020K_jDv8x_-ZQGKm86P2aqnOERUvKVr7sd7JvsH0QV5shlFuK6l-L90LDhZMm6MWJu5WV2jYmbmezpxm4DsWDc3hV6HgR_4rwibmW1X99l99e-g99eIBjvx6kihGvNcWgxNvYaUIvH5p-Bpx94H4BsH3NXtLd1OXsa851liEtu8LWjGuCb5b_RMz7GP3YiXb56Ao6sejuMr0ym8II5Ng;'
    return 'https://img.hulu.com/user/v3/artwork/{}&operations={}|cookie={}'.format(url.split('/')[-1], quote(operations), quote(cookie))

@plugin.route()
def live(**kwargs):
    folder = plugin.Folder(_.LIVE_CHANNELS)

    now = arrow.now()
    channels = api.channels()
    ids = [x['id'] for x in channels]
    epg_data = api.guide(ids, start=now, end=now.shift(hours=4))

    for channel in channels:
        plot = u''
        epg_count = 6
        for epg in epg_data.get(channel['id'], []):
            if epg['availabilityState'] != 'available':
                continue

            start = arrow.get(epg['airingStart']).replace(tzinfo='utc')
            stop = arrow.get(epg['airingEnd']).replace(tzinfo='utc')
            if (now > start and now < stop) or start > now:
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), epg['headline'])
                epg_count -= 1
                if not epg_count:
                    break

        folder.add_item(
            label = channel['name'],
            info = {'plot': plot},
            art = {'thumb': _image(channel['logoUrl'], 'live')},
            path = plugin.url_for(play_channel, channel_id=channel['id'], _is_live=True),
            playable = True,
        )

    return folder

@plugin.route()
def login(**kwargs):
    options = [
        [_.DEVICE_CODE, _device_code],
        [_.EMAIL_PASSWORD, _email_password],
    ]

    index = gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    _select_profile()
    gui.refresh()

def _device_code():
    timeout = 300
    code, serial = api.device_code()

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=DEVICE_ACTIVATE_URL, code=code), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                break

            progress.update(int((i / float(timeout)) * 100))
            if i % 5 == 0 and api.login_device(code, serial):
                return True

def _email_password():
    email = gui.input(_.ASK_EMAIL, default=userdata.get('email', '')).strip()
    if not email:
        return

    userdata.set('email', email)
    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(email, password)
    return True

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _select_profile():
    data = api.profiles()

    options = []
    values  = []
    default = -1

    for index, profile in enumerate(data['profiles']):
        values.append(profile)
        options.append(plugin.Item(label=_(_.KIDS_PROFILE, name=profile['name']) if profile['is_kids'] else profile['name']))
        if profile['id'] == userdata.get('profile_id'):
            default = index
            userdata.set('is_kids', profile['is_kids'])

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=False)
    if index < 0:
        return

    _set_profile(values[index], data['pin_enabled'])

def _set_profile(profile, pin_enabled=False):
    pin = None
    if pin_enabled and not profile['is_kids']:
        pin = gui.input(_.ENTER_PIN, hide_input=True).strip()

    api.set_profile(profile['id'], pin=pin)
    if settings.getBool('kid_lockdown', False) and profile['is_kids']:
        userdata.set('kid_lockdown', True)
    userdata.set('is_kids', profile['is_kids'])

    userdata.set('profile_name', profile['name'])
    gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'])

def _get_play_path(id, **kwargs):
    if not id:
        return None

    kwargs['id'] = id
    if settings.getBool('sync_playback', False):
        kwargs[NO_RESUME_TAG] = True
    else:
        profile_id = userdata.get('profile_id')
        if profile_id:
            kwargs['profile_id'] = profile_id

    return plugin.url_for(play, **kwargs)

@plugin.route()
@plugin.login_required()
def play_channel(channel_id, **kwargs):
    now = arrow.now()

    epg_data = api.guide([channel_id], start=now, end=now)
    if not epg_data.get(channel_id, []) or epg_data[channel_id][0].get('availabilityState') != 'available':
        raise PluginError(_.NO_LISTINGS)

    return _play(epg_data[channel_id][0]['eab'], play_type=PLAY_FROM_LIVE, **kwargs)

@plugin.route()
@plugin.login_required()
def play(id, play_type=None, **kwargs):
    return _play(id, play_type, **kwargs)

def _play(id, play_type, **kwargs):
    entities = []
    if '::' not in id or id.endswith('::NULL'):
        result = api.deeplink(id.replace('EAB::', '').split(':')[0])
        if not result:
            raise PluginError(_(_.NO_ENTITY, entity=id))
        id = result

    entities = api.entities([id])
    if not entities or 'bundle' not in entities[0]:
        raise PluginError(_(_.NO_ENTITY, entity=id))

    entity = entities[0]
    eab_id = entity['bundle']['eab_id']
    data = api.play(entity['bundle'])

    item = plugin.Item(
        path = data['stream_url'],
        inputstream = inputstream.Widevine(
            license_key = data['wv_server'],
        ),
        headers = HEADERS,
    )

    if ROUTE_LIVE_TAG in kwargs:
        if play_type is None:
            play_type = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)

        play_type = int(play_type)
        if play_type == PLAY_FROM_START:
            item.resume_from = 1
        elif play_type == PLAY_FROM_ASK:
            item.resume_from = plugin.live_or_start()
            if item.resume_from == -1:
                return

        if not item.resume_from:
            ## Need below to seek to live over multi-periods
            item.resume_from = LIVE_HEAD

        #item.inputstream.properties['manifest_update_parameter'] = 'full'

    if 'transcripts_urls' in data:
        subs = {}
        for _type in ('webvtt',): #ttml too slow to convert due to slow xml parser
            for key in data['transcripts_urls'].get(_type, {}):
                if key not in subs:
                    subs[key] = data['transcripts_urls'][_type][key]

        for key in subs:
            item.subtitles.append([subs[key], key])

    if data['asset_playback_type'] == 'VOD' and settings.getBool('sync_playback', False):
        if data.get('initial_position') and NO_RESUME_TAG in kwargs and not kwargs.get(ROUTE_RESUME_TAG):
            item.resume_from = plugin.resume_from(int(data['initial_position']/1000))
            if item.resume_from == -1:
                return

        item.callback = {
            'type':'interval',
            'interval': 30,
            'callback': plugin.url_for(update_progress, eab_id=eab_id),
        }

    return item

@plugin.route()
@plugin.no_error_gui()
def update_progress(eab_id, _time, **kwargs):
    api.update_progress(eab_id, int(_time))

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    userdata.delete('kid_lockdown')
    userdata.delete('profile_name')
    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(plugin.url_for(epg, output='$FILE')))

        for channel in api.channels():
            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=channel['id'], name=channel['name'], logo=_image(channel['logoUrl'], 'live'), url=plugin.url_for(play_channel, channel_id=channel['id'], _is_live=True),
            ))

@plugin.route()
@plugin.merge()
@plugin.login_required()
def epg(output, **kwargs):
    now = arrow.utcnow()
    channels = api.channels()
    ids = [x['id'] for x in channels]

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for channel in channels:
            f.write(u'<channel id="{id}"></channel>'.format(id=channel['id']))

        for i in range(0, settings.getInt('epg_days', 3)):
            epg_data = api.guide(ids, start=now.shift(days=i), end=now.shift(days=i+1))

            details = {}
            if i == 0:
                eabs = []
                for channel_id in epg_data:
                    for epg in epg_data[channel_id]:
                        if epg['availabilityState'] != 'available':
                            continue

                        eabs.append(epg['eab'])

                details = api.guide_details(eabs)

            for channel_id in epg_data:
                for epg in epg_data[channel_id]:
                    if epg['availabilityState'] != 'available':
                        continue

                    start = arrow.get(epg['airingStart']).replace(tzinfo='utc')
                    stop = arrow.get(epg['airingEnd']).replace(tzinfo='utc')

                    detail = details.get(epg['eab']) or {}
                    _type = detail.get('type')
                    series = detail.get('season_number') or 0
                    episode = detail.get('episode_number') or 0
                    icon = detail.get('artwork', {}).get('thumbnail')
                    desc = detail.get('description')
                    subtitle = detail.get('episode_name')

                    date = detail.get('premiere_date')
                    date = arrow.get(date).replace(tzinfo='utc') if date else None
                    new = u'<new></new>' if date and date.format('YYYYMMDDD') == start.format('YYYYMMDDD') else ''

                    if _type == 'movie':
                        category = 'Movie'
                    else:
                        category = date = None

                    episode = u'<episode-num system="onscreen">S{}E{}</episode-num>'.format(series, episode) if series > 0 and episode > 0 else ''
                    date = u'<date>{}</date>'.format(date.format('YYYYMMDD')) if date else ''
                    icon = u'<icon src="{}"/>'.format(escape(_image(icon))) if icon else ''
                    subtitle = u'<sub-title>{}</sub-title>'.format(escape(subtitle)) if subtitle else ''
                    desc = u'<desc>{}</desc>'.format(escape(desc)) if desc else ''
                    category = u'<category>{}</category>'.format(escape(category)) if category else ''

                    f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{subtitle}{icon}{episode}{desc}{date}{category}{new}</programme>'.format(
                        id=channel_id, start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(epg.get('headline','')), subtitle=subtitle, episode=episode, icon=icon, desc=desc, date=date, category=category, new=new))

        f.write(u'</tv>')
