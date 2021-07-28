from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.log import log
from slyguy.exceptions import PluginError
from slyguy.constants import KODI_VERSION, ROUTE_RESUME_TAG

from .api import API
from .constants import *
from .language import _

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True),  path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(collection, slug='home', content_class='home', label=_.FEATURED))
        folder.add_item(label=_(_.HUBS, _bold=True), path=plugin.url_for(sets, set_id=HUBS_SET_ID, set_type=HUBS_SET_TYPE))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(collection, slug='movies', content_class='contentType'))
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(collection, slug='series', content_class='contentType'))
        folder.add_item(label=_(_.ORIGINALS, _bold=True), path=plugin.url_for(collection, slug='originals', content_class='originals'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('disney_watchlist', False):
            folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(collection, slug='watchlist', content_class='watchlist'))

        if settings.getBool('disney_sync', False):
            folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(sets, set_id=CONTINUE_WATCHING_SET_ID, set_type=CONTINUE_WATCHING_SET_TYPE))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile')}, _kiosk=False, bookmark=False)

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
    _select_profile()
    gui.refresh()

@plugin.route()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _avatars(ids):
    avatars = {}

    data = api.avatar_by_id(ids)
    for row in data['avatars']:
        avatars[row['avatarId']] = row['image']['tile']['1.00']['avatar']['default']['url'] + '/scale?width=300'

    return avatars

def _select_profile():
    account = api.account()['account']
    profiles = account['profiles']
    avatars = _avatars([x['attributes']['avatar']['id'] for x in profiles])

    options = []
    values = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)
        profile['_avatar'] = avatars.get(profile['attributes']['avatar']['id'])

        if profile['attributes']['parentalControls']['isPinProtected']:
            label = _(_.PROFILE_WITH_PIN, name=profile['name'])
        else:
            label = profile['name']

        options.append(plugin.Item(label=label, art={'thumb': profile['_avatar']}))

        if account['activeProfile'] and profile['id'] == account['activeProfile']['id']:
            default = index
            userdata.set('avatar', profile['_avatar'])
            userdata.set('profile', profile['name'])
            userdata.set('profile_id', profile['id'])

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _switch_profile(values[index])

def _switch_profile(profile):
    pin = None
    if profile['attributes']['parentalControls']['isPinProtected']:
        pin = gui.input(_.ENTER_PIN, hide_input=True).strip()

    api.switch_profile(profile['id'], pin=pin)

    if settings.getBool('kid_lockdown', False) and profile['attributes']['kidsModeEnabled']:
        userdata.set('kid_lockdown', True)

    userdata.set('avatar', profile['_avatar'])
    userdata.set('profile', profile['name'])
    userdata.set('profile_id', profile['id'])
    gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=profile['_avatar'])

@plugin.route()
def collection(slug, content_class, label=None, **kwargs):
    data = api.collection_by_slug(slug, content_class)
    folder = plugin.Folder(label or _get_text(data['text'], 'title', 'collection'), thumb=_image(data.get('image', []), 'fanart'))

    for row in data['containers']:
        _type = row.get('type')
        _set = row.get('set')
        _style = row.get('style')
        ref_type = _set['refType'] if _set['type'] == 'SetRef' else _set['type']

        if _set.get('refIdType') == 'setId':
            set_id = _set['refId']
        else:
            set_id = _set.get('setId')

        if not set_id:
            return None

        if slug == 'home' and _style == 'brand':
            continue

        if _style in ('hero', 'WatchlistSet'):
            items = _process_rows(_set.get('items', []), content_class=_style)
            folder.add_items(items)
            continue

        elif _style == 'BecauseYouSet':
            data = api.set_by_id(set_id, _style, page_size=0)
            if not data['meta']['hits']:
                continue

            title = _get_text(data['text'], 'title', 'set')
        else:
            title = _get_text(_set['text'], 'title', 'set')

        folder.add_item(
            label = title,
            path = plugin.url_for(sets, set_id=set_id, set_type=ref_type),
        )

    return folder

@plugin.route()
def sets(set_id, set_type, page=1, **kwargs):
    page = int(page)
    data = api.set_by_id(set_id, set_type, page=page)

    folder = plugin.Folder(_get_text(data['text'], 'title', 'set'))

    items = _process_rows(data.get('items', []), data['type'])
    folder.add_items(items)

    if (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path  = plugin.url_for(sets, set_id=set_id, set_type=set_type, page=page+1),
            specialsort = 'bottom',
        )

    return folder

def _continue_watching():
    data = api.continue_watching()

    continue_watching = {}
    for row in data['items']:
        if row['meta']['bookmarkData']:
            play_from = row['meta']['bookmarkData']['playhead']
        else:
            play_from = 0

        continue_watching[row['family']['encodedFamilyId']] = play_from

    return continue_watching

def _process_rows(rows, content_class=None):
    items = []
    continue_watching = _continue_watching() if (settings.getBool('disney_sync', False) and content_class != CONTINUE_WATCHING_SET_TYPE) else {}

    for row in rows:
        item = None
        content_type = row.get('type')

        if content_type == 'DmcVideo':
            program_type = row.get('programType')

            if program_type == 'episode':
                if content_class in ('episode', CONTINUE_WATCHING_SET_TYPE):
                    item = _parse_video(row)
                else:
                    item = _parse_series(row)
            else:
                item = _parse_video(row)

            if item.playable and settings.getBool('disney_sync', False):
                try:
                    item.resume_from = row['meta']['bookmarkData']['playhead']
                except:
                    item.resume_from = continue_watching.get(row['family']['encodedFamilyId'], 0)

        elif content_type == 'DmcSeries':
            item = _parse_series(row)

        elif content_type == 'StandardCollection':
            item = _parse_collection(row)

        if not item:
            continue

        if settings.getBool('disney_watchlist', False):
            if content_class == 'WatchlistSet':
                item.context.insert(0, (_.DELETE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(delete_watchlist, content_id=row['contentId']))))
            elif (content_type == 'DmcSeries' or (content_type == 'DmcVideo' and program_type != 'episode')):
                item.context.insert(0, (_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, content_id=row['contentId'], title=item.label, icon=item.art.get('thumb')))))

        items.append(item)

    return items

@plugin.route()
def add_watchlist(content_id, title=None, icon=None, **kwargs):
    gui.notification(_.ADDED_WATCHLIST, heading=title, icon=icon)
    api.add_watchlist(content_id)

@plugin.route()
def delete_watchlist(content_id, **kwargs):
    api.delete_watchlist(content_id)
    gui.refresh()

def _parse_collection(row):
    return plugin.Item(
        label = _get_text(row['text'], 'title', 'collection'),
        info  = {'plot': _get_text(row['text'], 'description', 'collection')},
        art   = {'thumb': _image(row['image'], 'fanart')},
        path  = plugin.url_for(collection, slug=row['collectionGroup']['slugs'][0]['value'], content_class=row['collectionGroup']['contentClass']),
    )

def _get_play_path(content_id, skip_intro=None):
    kwargs = {
        'content_id': content_id,
        'profile_id': userdata.get('profile_id', ''),
    }

    if settings.getBool('disney_sync', False):
        kwargs['sync'] = 1

    if skip_intro != None:
        kwargs['skip_intro'] = skip_intro

    return plugin.url_for(play, **kwargs)

def _parse_series(row):
    return plugin.Item(
        label = _get_text(row['text'], 'title', 'series'),
        art = {'thumb': _image(row['image'], 'thumb'), 'fanart': _image(row['image'], 'fanart')},
        info = {
            'plot': _get_text(row['text'], 'description', 'series'),
            'year': row['releases'][0]['releaseYear'],
            'mediatype': 'tvshow',
        },
        context = ((_.INFORMATION, 'RunPlugin({})'.format(plugin.url_for(information, series_id=row['encodedSeriesId']))),),
        path = plugin.url_for(series, series_id=row['encodedSeriesId']),
    )

def _parse_season(row, series):
    title = _(_.SEASON, season=row['seasonSequenceNumber'])

    return plugin.Item(
        label = title,
        info  = {
            'plot': _get_text(row['text'], 'description', 'season') or _get_text(series['text'], 'description', 'series'),
            'year': row['releases'][0]['releaseYear'],
            'season': row['seasonSequenceNumber'],
            'mediatype': 'season',
        },
        art   = {'thumb': _image(row.get('image') or series['image'], 'thumb')},
        path  = plugin.url_for(season, season_id=row['seasonId'], title=title),
    )

def _parse_video(row):
    item = plugin.Item(
        label = _get_text(row['text'], 'title', 'program'),
        info  = {
            'plot': _get_text(row['text'], 'description', 'program'),
            'duration': row['mediaMetadata']['runtimeMillis']/1000,
            'year': row['releases'][0]['releaseYear'],
            'aired': row['releases'][0]['releaseDate'] or row['releases'][0]['releaseYear'],
            'mediatype': 'movie',
        },
        context = ((_.INFORMATION, 'RunPlugin({})'.format(plugin.url_for(information, family_id=row['family']['encodedFamilyId']))),),
        art  = {'thumb': _image(row['image'], 'thumb'), 'fanart': _image(row['image'], 'fanart')},
        path = _get_play_path(row['contentId']),
        playable = True,
    )

    if _get_milestone(row.get('milestone'), 'intro_end'):
        if settings.getBool('skip_intros', False):
            item.context.append((_.INCLUDE_INTRO, 'PlayMedia({},noresume)'.format(_get_play_path(row['contentId'], skip_intro=0))))
        else:
            item.context.append((_.SKIP_INTRO, 'PlayMedia({},noresume)'.format(_get_play_path(row['contentId'], skip_intro=1))))

    if row['programType'] == 'episode':
        item.info.update({
            'mediatype': 'episode',
            'season': row['seasonSequenceNumber'],
            'episode': row['episodeSequenceNumber'],
            'tvshowtitle': _get_text(row['text'], 'title', 'series'),
        })
    else:
        item.context.append((_.EXTRAS, "Container.Update({})".format(plugin.url_for(extras, family_id=row['family']['encodedFamilyId']))))
        item.context.append((_.SUGGESTED, "Container.Update({})".format(plugin.url_for(suggested, family_id=row['family']['encodedFamilyId']))))

    return item

def _image(data, _type='thumb', ratio='1.78'):
    _types = {
        'thumb': ('thumbnail', 'tile'),
        'fanart': ('background', 'background_details', 'hero_collection'),
    }

    selected = _types[_type]
    images = []

    for index, row in enumerate(selected):
        if row not in data or ratio not in data[row]:
            continue

        for row2 in data[row][ratio]:
            for row3 in data[row][ratio][row2]:
                images.append([index, data[row][ratio][row2][row3]])

    if not images:
        return None

    chosen = sorted(images, key=lambda x: (x[0], -x[1]['masterWidth']))[0][1]

    if _type == 'fanart':
        return chosen['url'] + '/scale?width=1440&aspectRatio=1.78&format=jpeg'
    else:
        return chosen['url'] + '/scale?width=400&aspectRatio=1.78&format=jpeg'

def _get_text(texts, field, source):
    _types = ['medium', 'brief', 'full']

    candidates = []
    for key in texts:
        if key != field:
            continue

        for _type in texts[key]:
            if _type not in _types or source not in texts[key][_type]:
                continue

            for row in texts[key][_type][source]:
                candidates.append((_types.index(_type), texts[key][_type][source][row]['content']))

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x[0])[0][1]

@plugin.route()
def series(series_id, **kwargs):
    data = api.series_bundle(series_id)

    title = _get_text(data['series']['text'], 'title', 'series')
    folder = plugin.Folder(title, fanart=_image(data['series']['image'], 'fanart'))

    for row in data['seasons']['seasons']:
        item = _parse_season(row, data['series'])
        folder.add_items(item)

    if data['extras']['videos']:
        folder.add_item(
            label = (_.EXTRAS),
            art   = {'thumb': _image(data['series']['image'], 'thumb')},
            path  = plugin.url_for(extras, series_id=series_id, fanart=_image(data['series']['image'], 'fanart')),
        )

    if data['related']['items']:
        folder.add_item(
            label = _.SUGGESTED,
            art   = {'thumb': _image(data['series']['image'], 'thumb')},
            path  = plugin.url_for(suggested, series_id=series_id),
        )

    return folder

@plugin.route()
def season(season_id, title, page=1, **kwargs):
    page = int(page)
    data = api.episodes(season_id, page=page)

    folder = plugin.Folder(title)

    items = _process_rows(data['videos'], content_class='episode')
    folder.add_items(items)

    if (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path  = plugin.url_for(season, season_id=season_id, title=title, page=page+1),
            specialsort = 'bottom',
        )

    return folder

@plugin.route()
def suggested(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
    elif series_id:
        data = api.series_bundle(series_id)

    folder = plugin.Folder(_.SUGGESTED)

    items = _process_rows(data['related']['items'])
    folder.add_items(items)
    return folder

@plugin.route()
def extras(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
        fanart = _image(data['video']['image'], 'fanart')
    elif series_id:
        data = api.series_bundle(series_id)
        fanart = _image(data['series']['image'], 'fanart')

    folder = plugin.Folder(_.EXTRAS, fanart=fanart)
    items = _process_rows(data['extras']['videos'])
    folder.add_items(items)
    return folder

@plugin.route()
def information(family_id=None, series_id=None, **kwargs):
    if series_id:
        data = api.series_bundle(series_id)
        item = _parse_series(data['series'])

    elif family_id:
        data = api.video_bundle(family_id)
        item = _parse_video(data['video'])

    gui.info(item)

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query)
    hits = [x['hit'] for x in data['hits']]
    return _process_rows(hits), False

@plugin.route()
@plugin.login_required()
def play(content_id=None, family_id=None, skip_intro=None, **kwargs):
    if KODI_VERSION > 18:
        ver_required = '2.6.0'
    else:
        ver_required = '2.4.5'

    ia = inputstream.Widevine(
        license_key = api.get_config()['services']['drm']['client']['endpoints']['widevineLicense']['href'],
        manifest_type = 'hls',
        mimetype = 'application/vnd.apple.mpegurl',
    )

    if not ia.check() or not inputstream.require_version(ver_required):
        gui.ok(_(_.IA_VER_ERROR, kodi_ver=KODI_VERSION, ver_required=ver_required))

    if family_id:
        data = api.video_bundle(family_id)
    else:
        data = api.video(content_id)

    video = data.get('video')
    if not video:
        raise PluginError(_.NO_VIDEO_FOUND)

    playback_url = video['mediaMetadata']['playbackUrls'][0]['href']
    playback_data = api.playback_data(playback_url)

    media_stream = playback_data['stream']['complete'][0]['url']
    original_language = video.get('originalLanguage') or 'en'

    headers = api.session.headers
    ia.properties['original_audio_language'] = original_language

    item = _parse_video(video)
    item.update(
        path = media_stream,
        inputstream = ia,
        headers = headers,
        proxy_data = {'default_language': original_language, 'original_language': original_language},
    )

    milestones = video.get('milestone', [])
    item.play_next = {}
    item.play_skips = []

    if kwargs[ROUTE_RESUME_TAG] and settings.getBool('disney_sync', False):
        continue_watching = _continue_watching()
        item.resume_from = continue_watching.get(video['contentId'], 0)
        item.force_resume = True

    elif milestones and (int(skip_intro) if skip_intro is not None else settings.getBool('skip_intros', False)):
        intro_start = _get_milestone(milestones, 'intro_start')
        intro_end = _get_milestone(milestones, 'intro_end')

        if intro_start <= 10 and intro_end > intro_start:
            item.resume_from = intro_end
        elif intro_start > 0 and intro_end > intro_start:
            item.play_skips.append({'from': intro_start, 'to': intro_end})

    if milestones and settings.getBool('skip_credits', False):
        next_start = _get_milestone(milestones, 'up_next')
        item.play_next['time'] = next_start

    if video['programType'] == 'episode' and settings.getBool('play_next_episode', True):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] == 'episode' and row['encodedSeriesId'] == video['encodedSeriesId']:
                item.play_next['next_file'] = _get_play_path(row['contentId'])
                break

    elif video['programType'] != 'episode' and settings.getBool('play_next_movie', False):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] != 'episode':
                item.play_next['next_file'] = _get_play_path(row['contentId'])
                break

    if settings.getBool('wv_secure', False):
        item.inputstream.properties['license_flags'] = 'force_secure_decoder'

    if settings.getBool('disney_sync', False):
        telemetry = playback_data['tracking']['telemetry']
        item.callback = {
            'type':'interval',
            'interval': 30,
            'callback': plugin.url_for(callback, media_id=telemetry['mediaId'], fguid=telemetry['fguid']),
        }

    return item

@plugin.route()
@plugin.no_error_gui()
def callback(media_id, fguid, _time, **kwargs):
    api.update_resume(media_id, fguid, int(_time))

def _get_milestone(milestones, name, default=0):
    if not milestones:
        return default

    for key in milestones:
        if key == name:
            return int(milestones[key][0]['milestoneTime'][0]['startMillis'] / 1000)

    return default

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    userdata.delete('avatar')
    userdata.delete('profile')
    userdata.delete('profile_id')
    gui.refresh()
