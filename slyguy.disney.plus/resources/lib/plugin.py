import sys
import random
import datetime

import arrow
from kodi_six import xbmcplugin

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
        folder.add_item(label=_(_.HUBS, _bold=True),  path=plugin.url_for(hubs))
        folder.add_item(label=_(_.MOVIES, _bold=True),  path=plugin.url_for(collection, slug='movies', content_class='contentType'))
        folder.add_item(label=_(_.SERIES, _bold=True),  path=plugin.url_for(collection, slug='series', content_class='contentType'))
        folder.add_item(label=_(_.ORIGINALS, _bold=True),  path=plugin.url_for(collection, slug='originals', content_class='originals'))
        folder.add_item(label=_(_.WATCHLIST, _bold=True),  path=plugin.url_for(collection, slug='watchlist', content_class='watchlist'))
        folder.add_item(label=_(_.SEARCH, _bold=True),  path=plugin.url_for(search))

        if settings.getBool('disney_sync', False):
            folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(sets, set_id=CONTINUE_WATCHING_SET_ID, set_type=CONTINUE_WATCHING_SET_TYPE))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile')}, _kiosk=False, bookmark=False)
            #folder.add_item(label=_.PROFILE_SETTINGS, path=plugin.url_for(profile_settings), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile')}, _kiosk=False)

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
def hubs(**kwargs):
    folder = plugin.Folder(_.HUBS)

    data = api.collection_by_slug('home', 'home')
    thumb = _image(data.get('images', []), 'thumb')

    for row in data['containers']:
        _set = row.get('set')
        if _set.get('contentClass') == 'brandSix':
            items = _process_rows(_set.get('items', []), 'brand')
            folder.add_items(items)

    return folder

@plugin.route()
def edit_profile(key, value, **kwargs):
    profile = api.active_profile()

    if key == 'prefer_133':
        profile['attributes']['playbackSettings']['prefer133'] = bool(int(value))

    if api.update_profile(profile):
        gui.refresh()

# @plugin.route()
# def profile_settings(**kwargs):
#     folder = plugin.Folder(_.PROFILE_SETTINGS)

#     profile = api.active_profile()

#     app_language      = profile['attributes']['languagePreferences']['appLanguage']
#     playback_language = profile['attributes']['languagePreferences']['playbackLanguage']
#     subtitle_language = profile['attributes']['languagePreferences']['subtitleLanguage']
#     prefer_133        = profile['attributes']['playbackSettings']['prefer133']

#     # folder.add_item(label='App Language: {}'.format(app_language))
#     # folder.add_item(label='Playback Language: {}'.format(playback_language))
#     # folder.add_item(label='Subtitle Language: {}'.format(subtitle_language))
#     folder.add_item(label='Prefer Original Video Format: {}'.format('Yes' if prefer_133 else 'No'), path=plugin.url_for(edit_profile, key='prefer_133', value=int(not prefer_133)))

#     return folder

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
        avatars[row['avatarId']] = row['images'][0]['url']

    return avatars

def _select_profile():
    profiles = api.profiles()
    active   = api.active_profile()
    avatars  = _avatars([x['attributes']['avatar']['id'] for x in profiles])

    options = []
    values  = []
    can_delete = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)
        profile['_avatar'] = avatars.get(profile['attributes']['avatar']['id'])

        if profile['attributes']['parentalControls']['isPinProtected']:
            label = _(_.PROFILE_WITH_PIN, name=profile['profileName'])
        else:
            label = profile['profileName']

        options.append(plugin.Item(label=label, art={'thumb': profile['_avatar']}))

        if profile['profileId'] == active.get('profileId'):
            default = index

            userdata.set('avatar', profile['_avatar'])
            userdata.set('profile', profile['profileName'])
            userdata.set('profile_id', profile['profileId'])

        elif not profile['attributes']['isDefault']:
            can_delete.append(profile)

    options.append(plugin.Item(label=_(_.ADD_PROFILE, _bold=True)))
    values.append('_add')

    if can_delete:
        options.append(plugin.Item(label=_(_.DELETE_PROFILE, _bold=True)))
        values.append('_delete')

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)

    if index < 0:
        return

    selected = values[index]

    if selected == '_delete':
        _delete_profile(can_delete)
    elif selected == '_add':
        _add_profile(taken_names=[x['profileName'] for x in profiles], taken_avatars=[avatars[x] for x in avatars])
    else:
        _set_profile(selected)

def _set_profile(profile):
    pin = None
    if profile['attributes']['parentalControls']['isPinProtected']:
        pin = gui.input(_.ENTER_PIN, hide_input=True).strip()

    api.set_profile(profile, pin=pin)

    if settings.getBool('kid_lockdown', False) and profile['attributes']['kidsModeEnabled']:
        userdata.set('kid_lockdown', True)

    userdata.set('avatar', profile['_avatar'])
    userdata.set('profile', profile['profileName'])
    userdata.set('profile_id', profile['profileId'])
    gui.notification(_.PROFILE_ACTIVATED, heading=profile['profileName'], icon=profile['_avatar'])

def _delete_profile(profiles):
    options = []
    for index, profile in enumerate(profiles):
        options.append(plugin.Item(label=profile['profileName'], art={'thumb': profile['_avatar']}))

    index = gui.select(_.SELECT_DELETE_PROFILE, options=options, useDetails=True)
    if index < 0:
        return

    selected = profiles[index]
    if gui.yes_no(_.DELETE_PROFILE_INFO, heading=_(_.DELTE_PROFILE_HEADER, name=selected['profileName'])) and api.delete_profile(selected).ok:
        gui.notification(_.PROFILE_DELETED, heading=selected['profileName'], icon=selected['_avatar'])

def _add_profile(taken_names, taken_avatars):
    ## PROFILE AVATAR ##
    options = [plugin.Item(label=_(_.RANDOM_AVATAR, _bold=True)),]
    values  = ['_random',]
    avatars = {}
    unused  = []

    data = api.collection_by_slug('avatars', 'avatars')
    for container in data['containers']:
        if container['set']['contentClass'] == 'hidden':
            continue

        category = _get_text(container['set']['texts'], 'title', 'set')

        for row in container['set'].get('items', []):
            if row['images'][0]['url'] in taken_avatars:
                label = _(_.AVATAR_USED, label=category)
            else:
                label = category
                unused.append(row['avatarId'])

            options.append(plugin.Item(label=label, art={'thumb': row['images'][0]['url']}))
            values.append(row['avatarId'])
            avatars[row['avatarId']] = row['images'][0]['url']

    index = gui.select(_.SELECT_AVATAR, options=options, useDetails=True)
    if index < 0:
        return

    avatar = values[index]
    if avatar == '_random':
        avatar = random.choice(unused or avatars.keys())

    ## PROFLE KIDS ##
    kids = gui.yes_no(_.KIDS_PROFILE_INFO, heading=_.KIDS_PROFILE)

    ## PROFILE NAME ##
    name = ''
    while True:
        name = gui.input(_.PROFILE_NAME, default=name).strip()
        if not name:
            return

        elif name in taken_names:
            gui.notification(_(_.PROFILE_NAME_TAKEN, name=name))

        else:
            break

    profile = api.add_profile(name, kids=kids, avatar=avatar)
    profile['_avatar'] = avatars[avatar]

    if 'errors' in profile:
        raise PluginError(profile['errors'][0].get('description'))

    _set_profile(profile)

@plugin.route()
def collection(slug, content_class, label=None, **kwargs):
    data = api.collection_by_slug(slug, content_class)

    folder = plugin.Folder(label or _get_text(data['texts'], 'title', 'collection'), fanart=_image(data.get('images', []), 'fanart'))
    thumb  = _image(data.get('images', []), 'thumb')

    for row in data['containers']:
        _type = row.get('type')
        _set  = row.get('set')

        if _set.get('refIdType') == 'setId':
            set_id = _set['refId']
        else:
            set_id = _set.get('setId')

        if not set_id:
            return None

        if slug == 'home' and _set['contentClass'] == 'brandSix':
            continue

       # if _set['contentClass'] in ('hero', 'episode', 'WatchlistSet'): # dont think need episode here..
        if _set['contentClass'] in ('hero', 'WatchlistSet'):
            items = _process_rows(_set.get('items', []), _set['contentClass'])
            folder.add_items(items)
            continue

        elif _set['contentClass'] == 'BecauseYouSet':
            data = api.set_by_id(set_id, _set['contentClass'], page_size=0)
            if not data['meta']['hits']:
                continue

            title = _get_text(data['texts'], 'title', 'set')

        else:
            title = _get_text(_set['texts'], 'title', 'set')

        folder.add_item(
            label = title,
            art   = {'thumb': thumb},
            path  = plugin.url_for(sets, set_id=set_id, set_type=_set['contentClass']),
        )

    return folder

@plugin.route()
def sets(set_id, set_type, page=1, **kwargs):
    page = int(page)
    data = api.set_by_id(set_id, set_type, page=page)

    folder = plugin.Folder(_get_text(data['texts'], 'title', 'set'), sort_methods=[xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_VIDEO_YEAR, xbmcplugin.SORT_METHOD_LABEL])

    items = _process_rows(data.get('items', []), data['contentClass'])
    folder.add_items(items)

    if (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path  = plugin.url_for(sets, set_id=set_id, set_type=set_type, page=page+1),
            specialsort = 'bottom',
        )

    return folder

def _process_rows(rows, content_class=None):
    items = []
    continue_watching = {}

    if settings.getBool('disney_sync', False):
        continue_watching = api.continue_watching()

    for row in rows:
        item = None
        content_type = row.get('type')

        if content_type == 'DmcVideo':
            program_type = row.get('programType')

            if program_type == 'episode':
                if content_class in ('episode', 'ContinueWatchingSet'):
                    item = _parse_video(row)
                else:
                    item = _parse_series(row)
            else:
                item = _parse_video(row)

            if item.playable and settings.getBool('disney_sync', False):
                item.properties['ResumeTime'] = continue_watching.get(row['contentId'], 0)
                item.properties['TotalTime'] = continue_watching.get(row['contentId'], 0)

        elif content_type == 'DmcSeries':
            item = _parse_series(row)

        elif content_type == 'StandardCollection':
            item = _parse_collection(row)

        if not item:
            continue

        if content_class == 'WatchlistSet':
            item.context.insert(0, (_.DELETE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(delete_watchlist, content_id=row['contentId']))))
        elif content_type == 'DmcSeries' or (content_type == 'DmcVideo' and program_type != 'episode'):
            item.context.insert(0, (_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, content_id=row['contentId'], title=item.label, icon=item.art.get('thumb')))))

        items.append(item)

    return items

@plugin.route()
def add_watchlist(content_id, title=None, icon=None, **kwargs):
    gui.notification(_.ADDED_WATCHLIST, heading=title, icon=icon)
    api.add_watchlist(content_id)

@plugin.route()
def delete_watchlist(content_id, **kwargs):
    data = api.delete_watchlist(content_id)

    if not data.get('watchlistItems'):
        gui.redirect(plugin.url_for(''))
    else:
        gui.refresh()

def _parse_collection(row):
    return plugin.Item(
        label = _get_text(row['texts'], 'title', 'collection'),
        info  = {'plot': _get_text(row['texts'], 'description', 'collection')},
        art   = {'thumb': _image(row['images'], 'thumb'), 'fanart': _image(row['images'], 'fanart')},
        path  = plugin.url_for(collection, slug=row['collectionGroup']['slugs'][0]['value'], content_class=row['collectionGroup']['contentClass']),
    )

def _parse_series(row):
    return plugin.Item(
        label = _get_text(row['texts'], 'title', 'series'),
        art = {'thumb': _image(row['images'], 'thumb'), 'fanart': _image(row['images'], 'fanart')},
        info = {
            'plot': _get_text(row['texts'], 'description', 'series'),
            'year': row['releases'][0]['releaseYear'],
      #      'mediatype': 'tvshow',
            'genre': row['genres'],
        },
        path = plugin.url_for(series, series_id=row['encodedSeriesId']),
    )

def _parse_season(row, series):
    title = _(_.SEASON, season=row['seasonSequenceNumber'])

    return plugin.Item(
        label = title,
        info  = {
            'plot': _get_text(row['texts'], 'description', 'season'),
            'year': row['releases'][0]['releaseYear'],
            'season': row['seasonSequenceNumber'],
           # 'mediatype' : 'season'
        },
        art   = {'thumb': _image(row['images'] or series['images'], 'thumb')},
        path  = plugin.url_for(season, season_id=row['seasonId'], title=title),
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

def _parse_video(row):
    item = plugin.Item(
        label = _get_text(row['texts'], 'title', 'program'),
        info  = {
            'plot': _get_text(row['texts'], 'description', 'program'),
            'duration': row['mediaMetadata']['runtimeMillis']/1000,
            'year': row['releases'][0]['releaseYear'],
            'dateadded': row['releases'][0]['releaseDate'] or row['releases'][0]['releaseYear'],
            'mediatype': 'movie',
            'genre': row['genres'],
            'season': row['seasonSequenceNumber'],
            'episode': row['episodeSequenceNumber'],
        },
        art  = {'thumb': _image(row['images'], 'thumb'), 'fanart': _image(row['images'], 'fanart')},
        path = _get_play_path(row['contentId']),
        playable = True,
    )

    if _get_milestone(row.get('milestones'), 'intro_end'):
        if settings.getBool('skip_intros', False):
            item.context.append((_.INCLUDE_INTRO, 'PlayMedia({},noresume)'.format(_get_play_path(row['contentId'], skip_intro=0))))
        else:
            item.context.append((_.SKIP_INTRO, 'PlayMedia({},noresume)'.format(_get_play_path(row['contentId'], skip_intro=1))))

    if row['programType'] == 'episode':
        item.info.update({
            'mediatype' : 'episode',
            'tvshowtitle': _get_text(row['texts'], 'title', 'series'),
        })
    else:
        item.context.append((_.EXTRAS, "Container.Update({})".format(plugin.url_for(extras, family_id=row['encodedParentOf'], fanart=_image(row['images'], 'fanart')))))
        item.context.append((_.SUGGESTED, "Container.Update({})".format(plugin.url_for(suggested, family_id=row['encodedParentOf']))))

    if row['currentAvailability']['appears']:
        available = arrow.get(row['currentAvailability']['appears'])
        if available > arrow.now():
            item.label = _(_.AVAILABLE, label=item.label, date=available.to('local').format(_.AVAILABLE_FORMAT))

    return item

def _image(data, _type='thumb'):
    _types = {
        'thumb': (('thumbnail','1.78'), ('tile','1.78')),
        'fanart': (('background','1.78'), ('background_details','1.78'), ('hero_collection','1.78')),
    }

    selected = _types[_type]

    images = []
    for row in data:
        for index, _type in enumerate(selected):
            if not row['url']:
                continue

            if row['purpose'] == _type[0] and str(row['aspectRatio']) == _type[1]:
                images.append([index, row])

    if not images:
        return None

    chosen = sorted(images, key=lambda x: (x[0], -x[1]['masterWidth']))[0][1]

    if _type == 'fanart':
        return chosen['url'] + '/scale?aspectRatio=1.78&format=jpeg'
    else:
        return chosen['url'] + '/scale?width=800&aspectRatio=1.78&format=jpeg'

def _get_text(texts, field, source):
    _types = ['medium', 'brief', 'full']

    candidates = []
    for row in texts:
        if row['field'] == field and source == row['sourceEntity']:
            if not row['content']:
                continue

            if row['type'] not in _types:
                _types.append(row['type'])

            candidates.append((_types.index(row['type']), row['content']))

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x[0])[0][1]

@plugin.route()
def series(series_id, **kwargs):
    data = api.series_bundle(series_id, page_size=0)

    title = _get_text(data['series']['texts'], 'title', 'series')
    folder = plugin.Folder(title, fanart=_image(data['series']['images'], 'fanart'))

    for row in data['seasons']['seasons']:
        item = _parse_season(row, data['series'])
        folder.add_items(item)

    if data['extras']['videos']:
        folder.add_item(
            label = (_.EXTRAS),
            art   = {'thumb': _image(data['series']['images'], 'thumb')},
            path  = plugin.url_for(extras, family_id=data['series']['family']['encodedFamilyId'], fanart=_image(data['series']['images'], 'fanart')),
        )

    if data['related']['items']:
        folder.add_item(
            label = _.SUGGESTED,
            art   = {'thumb': _image(data['series']['images'], 'thumb')},
            path  = plugin.url_for(suggested, series_id=series_id),
        )

    return folder

@plugin.route()
def season(season_id, title, page=1, **kwargs):
    page = int(page)
    data = api.episodes([season_id,], page=page)

    folder = plugin.Folder(title, sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])

    items = _process_rows(data['videos'], content_class='episode')
    folder.add_items(items)

    if ((data['meta']['episode_page_size'] * data['meta']['episode_page']) < data['meta']['max_hits_per_season']):
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
        data = api.series_bundle(series_id, page_size=0)

    folder = plugin.Folder(_.SUGGESTED)

    items = _process_rows(data['related']['items'])
    folder.add_items(items)

    return folder

@plugin.route()
def extras(family_id, fanart=None, **kwargs):
    folder = plugin.Folder(_.EXTRAS, fanart=fanart)
    data = api.extras(family_id)
    items = _process_rows(data['videos'])
    folder.add_items(items)
    return folder

@plugin.route()
def search(query=None, page=1, **kwargs):
    page  = int(page)

    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    data = api.search(query, page=page)

    hits = [x['hit'] for x in data['hits']] if data['resultsType'] == 'real' else []
    items = _process_rows(hits)
    folder.add_items(items)

    if (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path  = plugin.url_for(search, query=query, page=page+1),
            specialsort = 'bottom',
        )

    return folder

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
        if not data.get('video'):
            raise PluginError(_.NO_VIDEO_FOUND)

        video = data['video']
    else:
        data = api.videos(content_id)
        if not data.get('videos'):
            raise PluginError(_.NO_VIDEO_FOUND)

        video = data['videos'][0]

    playback_url      = video['mediaMetadata']['playbackUrls'][0]['href']
    playback_data     = api.playback_data(playback_url)
    media_stream      = playback_data['stream']['complete']
    original_language = video.get('originalLanguage') or 'en'

    headers = api.session.headers
    ia.properties['original_audio_language'] = original_language

    ## Allow fullres worldwide ##
    media_stream = media_stream.replace('/mickey/ps01/', '/ps01/')
    ##############

    item = _parse_video(video)
    item.update(
        path = media_stream,
        inputstream = ia,
        headers = headers,
        use_proxy = True, #required for default languages
        proxy_data = {'default_language': original_language, 'original_language': original_language},
    )

    resume_from = None
    if kwargs[ROUTE_RESUME_TAG]:
        if settings.getBool('disney_sync', False):
            continue_watching = api.continue_watching()
            resume_from = continue_watching.get(video['contentId'], 0)
            item.properties['ForceResume'] = True

    elif (int(skip_intro) if skip_intro is not None else settings.getBool('skip_intros', False)):
        resume_from = _get_milestone(video.get('milestones'), 'intro_end', default=0) / 1000

    if resume_from is not None:
        item.properties['ResumeTime'] = resume_from
        item.properties['TotalTime']  = resume_from

    item.play_next = {}

    if settings.getBool('skip_credits', False):
        next_start = _get_milestone(video.get('milestones'), 'up_next', default=0) / 1000
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
            'interval': 20,
            'callback': plugin.url_for(callback, media_id=telemetry['mediaId'], fguid=telemetry['fguid']),
        }

    return item

@plugin.route()
@plugin.no_error_gui()
def callback(media_id, fguid, _time, **kwargs):
    api.update_resume(media_id, fguid, int(_time))

def _get_milestone(milestones, key, default=None):
    if not milestones:
        return default

    for milestone in milestones:
        if milestone['milestoneType'] == key:
            return milestone['milestoneTime'][0]['startMillis']

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