import re

from kodi_six import xbmc

from slyguy import plugin, gui, userdata, signals, inputstream
from slyguy.log import log
from slyguy.exceptions import PluginError
from slyguy.constants import KODI_VERSION, NO_RESUME_TAG, ROUTE_RESUME_TAG
from slyguy.drm import is_wv_secure
from slyguy.util import async_tasks

from .api import API
from .constants import *
from .language import _
from .settings import settings, Ratio


api = API()


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in


@plugin.route('')
def index(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(collection, slug='home', content_class='home', label=_.FEATURED))
        folder.add_item(label=_(_.HUBS, _bold=True), path=plugin.url_for(hubs))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(collection, slug='movies', content_class='contentType'))
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(collection, slug='series', content_class='contentType'))
        folder.add_item(label=_(_.ORIGINALS, _bold=True), path=plugin.url_for(collection, slug='originals', content_class='originals'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.SYNC_WATCHLIST.value:
            folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(watchlist))

        if settings.SYNC_PLAYBACK.value:
            folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(continue_watching))

        if settings.BOOKMARKS.value:
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder


@plugin.route()
def login(**kwargs):
    options = [
        [_.EMAIL_PASSWORD, _email_password],
     #   [_.DEVICE_CODE, _device_code],
    ]

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    _select_profile()
    gui.refresh()


def _device_code():
    monitor = xbmc.Monitor()
    code = api.device_code()
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=code, url=DEVICE_CODE_URL), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int((i / float(timeout)) * 100))

            if i % 5 == 0 and api.device_login(code):
                return True


def _email_password():
    email = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
    if not email:
        return

    userdata.set('username', email)

    token = api.register_device()
    next_step = api.check_email(email, token)

    if next_step.lower() == 'register':
        raise PluginError(_.EMAIL_NOT_FOUND)

    elif next_step.lower() == 'otp':
        api.request_otp(email, token)

        while True:
            otp = gui.input(_(_.OTP_INPUT, email=email)).strip()
            if not otp:
                return

            error = api.login_otp(email, otp, token)
            if not error:
                return True

            gui.error(error)
    else:
        password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
        if not password:
            return

        api.login(email, password, token)
        return True


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
    data = api.collection_by_slug(slug, content_class, 'PersonalizedCollection' if slug == 'home' else 'StandardCollection')
    folder = plugin.Folder(label or _get_text(data, 'title', 'collection'), thumb=_get_art(data).get('fanart'))
    if not data:
        return folder

    def process_row(row):
        _set = row.get('set')
        _style = row.get('style')
        ref_type = _set['refType'] if _set['type'] == 'SetRef' else _set['type']

        if _set.get('refIdType') == 'setId':
            set_id = _set['refId']
        else:
            set_id = _set.get('setId')

        if not set_id:
            return

        if slug == 'home' and (_style in ('brand', 'brandSix', 'hero', 'heroInteractive') or ref_type in ('ContinueWatchingSet', 'WatchlistSet')):
            return

        title = _get_text(_set, 'title', 'set')

        if not title or '{title}' in title:
            data = api.set_by_id(set_id, ref_type, page_size=0)
            # if not data['meta']['hits']:
            #     return
            title = _get_text(data, 'title', 'set')
            if not title or '{title}' in title:
                return

        return title, plugin.url_for(sets, set_id=set_id, set_type=ref_type)

    tasks = [lambda row=row: process_row(row) for row in data['containers']]
    results = [x for x in async_tasks(tasks) if x]
    for row in results:
        folder.add_item(
            label = row[0],
            path = row[1],
        )

    return folder


@plugin.route()
def hubs(**kwargs):
    page_id = api.explore_deeplink(ref_id='home', ref_type='deeplinkId')['actions'][0]['pageId']
    page = api.explore_page(page_id)
    set_id = [x for x in page['containers'] if x['visuals']['name'] == 'Brands'][0]['id']
    data = api.explore_set(set_id)
    folder = _process_explore(data)
    folder.title = _.HUBS
    return folder


@plugin.route()
def watchlist(**kwargs):
    page_id = api.explore_deeplink(ref_id='watchlist', ref_type='deeplinkId')['actions'][0]['pageId']
    set_id = api.explore_page(page_id)['containers'][0]['id']
    data = api.explore_set(set_id)
    folder = _process_explore(data, watchlist=True)
    folder.title = _.WATCHLIST
    return folder


@plugin.route()
def continue_watching(**kwargs):
    page_id = api.explore_deeplink(ref_id='home', ref_type='deeplinkId')['actions'][0]['pageId']
    page = api.explore_page(page_id)
    set_id = [x for x in page['containers'] if x['style']['name'] == 'continue_watching'][0]['id']
    data = api.explore_set(set_id)
    return _process_explore(data)


@plugin.route()
def sets(**kwargs):
    return _sets(**kwargs)


@plugin.pagination()
def _sets(set_id, set_type, page=1, **kwargs):
    data = api.set_by_id(set_id, set_type, page=page)
    folder = plugin.Folder(_get_text(data, 'title', 'set'))
    items = _process_rows(data.get('items', []), data['type'])
    folder.add_items(items)
    return folder, (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']


def _process_rows(rows, content_class=None):
    watchlist_enabled = settings.getBool('sync_watchlist', True)

    items = []
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

        elif content_type == 'DmcSeries':
            item = _parse_series(row)

        elif content_type in ('PersonalizedCollection', 'StandardCollection'):
            item = _parse_collection(row)

        if not item:
            continue

        ref_types = ['programId', 'seriesId']
        ref_type = None
        for _type in ref_types:
            if row.get(_type):
                ref_type = _type
                break

        if watchlist_enabled and ref_type:
            if content_class == 'WatchlistSet':
                item.context.append((_.DELETE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(delete_watchlist, ref_type=ref_type, ref_id=row[ref_type]))))
            elif (content_type == 'DmcSeries' or (content_type == 'DmcVideo' and program_type != 'episode')):
                item.context.append((_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, ref_type=ref_type, ref_id=row[ref_type], title=item.label, icon=item.art.get('thumb')))))

        items.append(item)

    return items


@plugin.route()
def add_watchlist(ref_type, ref_id, title=None, icon=None, **kwargs):
    gui.notification(_.ADDED_WATCHLIST, heading=title, icon=icon)
    api.add_watchlist(ref_type, ref_id)


@plugin.route()
def delete_watchlist(ref_type, ref_id, **kwargs):
    api.delete_watchlist(ref_type, ref_id)
    gui.refresh()


def _parse_collection(row):
    path = plugin.url_for(collection, slug=row['collectionGroup']['slugs'][0]['value'], content_class=row['collectionGroup']['contentClass'])

    if row.get('actions', []) and row['actions'][0]['type'] == 'browse':
        path = plugin.url_for(explore_page, page_id=row['actions'][0]['pageId'])

    return plugin.Item(
        label = _get_text(row, 'title', 'collection'),
        info = {'plot': _get_text(row, 'description', 'collection')},
        art = _get_art(row),
        path = path,
    )


def _get_play_path(**kwargs):
    if not kwargs:
        return None

    profile_id = userdata.get('profile_id')
    if profile_id:
        kwargs['profile_id'] = profile_id

    if settings.getBool('sync_playback', False):
        kwargs[NO_RESUME_TAG] = True

    return plugin.url_for(play, **kwargs)


def _parse_series(row):
    item = plugin.Item(
        label = _get_text(row, 'title', 'series'),
        art = _get_art(row),
        info = {
            'plot': _get_text(row, 'description', 'series'),
            'mediatype': 'tvshow',
            'trailer': plugin.url_for(play_trailer, series_id=row['encodedSeriesId']),
        },
        path = plugin.url_for(series, series_id=row['encodedSeriesId']),
    )

    try:
        item.info['year'] = row['releases'][0]['releaseYear']
    except IndexError:
        pass

    if not item.info['plot']:
        item.context.append((_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, series_id=row['encodedSeriesId']))))

    return item


def _parse_season(row, series):
    title = _(_.SEASON, number=row['seasonSequenceNumber'])

    item = plugin.Item(
        label = title,
        info  = {
            'plot': _get_text(row, 'description', 'season') or _get_text(series, 'description', 'series'),
            'season': row['seasonSequenceNumber'],
            'mediatype': 'season',
        },
        art   = _get_art(row) or _get_art(series),
        path  = plugin.url_for(season, season_id=row['seasonId'], title=title),
    )

    try:
        item.info['year'] = row['releases'][0]['releaseYear']
    except IndexError:
        pass

    return item


def _parse_video(row):
    item = plugin.Item(
        label = _get_text(row, 'title', 'program'),
        info  = {
            'plot': _get_text(row, 'description', 'program'),
            'duration': row['mediaMetadata']['runtimeMillis']/1000,
            'mediatype': 'movie',
            'trailer': plugin.url_for(play_trailer, family_id=row['family']['encodedFamilyId']),
        },
        art  = _get_art(row),
        path = _get_play_path(content_id=row['contentId']),
        playable = True,
    )

    try:
        item.info['year'] = row['releases'][0]['releaseYear']
        item.info['aired'] = row['releases'][0]['releaseDate']
    except IndexError:
        pass

    if row['programType'] == 'episode':
        item.info.update({
            'mediatype': 'episode',
            'season': row['seasonSequenceNumber'],
            'episode': row['episodeSequenceNumber'],
            'tvshowtitle': _get_text(row, 'title', 'series'),
        })
    else:
        if not item.info['plot']:
            item.context.append((_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, family_id=row['family']['encodedFamilyId']))))
        item.context.append((_.EXTRAS, "Container.Update({})".format(plugin.url_for(extras, family_id=row['family']['encodedFamilyId']))))
        item.context.append((_.SUGGESTED, "Container.Update({})".format(plugin.url_for(suggested, family_id=row['family']['encodedFamilyId']))))

    return item


def _get_art(row):
    if not row:
        return {}

    if 'image' in row:
        # api 5.1
        images = row['image']
    elif 'images' in row:
        #api 3.1
        images = {}
        for data in row['images']:
            if data['purpose'] not in images:
                images[data['purpose']] = {}
            images[data['purpose']][str(data['aspectRatio'])] = {data['sourceEntity']: {'default': data}}
    else:
        return None

    def _first_image_url(d):
        for r1 in d:
            for r2 in d[r1]:
                return d[r1][r2]['url']

    art = {}
    # don't ask for jpeg thumb; might be transparent png instead
    thumbsize = '/scale?width=800&aspectRatio=1.78'
    bannersize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'
    fullsize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'

    thumb_ratios = ['1.78', '1.33', '1.00']
    poster_ratios = ['0.71', '0.75', '0.80']
    clear_ratios = ['2.00', '1.78', '3.32']
    banner_ratios = ['3.91', '3.00', '1.78']

    fanart_count = 0
    is_episode = row.get('programType') == 'episode'

    if is_episode:
        thumbs = ('thumbnail',)
    else:
        thumbs = ('thumbnail', 'tile')

    for name in images or []:
        art_type = images[name]

        tr = br = pr = ''

        for ratio in thumb_ratios:
            if ratio in art_type:
                tr = ratio
                break

        for ratio in banner_ratios:
            if ratio in art_type:
                br = ratio
                break

        for ratio in poster_ratios:
            if ratio in art_type:
                pr = ratio
                break

        for ratio in clear_ratios:
            if ratio in art_type:
                cr = ratio
                break

        if name in thumbs:
            if tr:
                art['thumb'] = _first_image_url(art_type[tr]) + thumbsize
            if pr:
                art['poster'] = _first_image_url(art_type[pr]) + thumbsize

        elif name == 'hero_tile':
            if br:
                art['banner'] = _first_image_url(art_type[br]) + bannersize

        elif name in ('hero_collection', 'background_details', 'background'):
            if tr:
                k = 'fanart{}'.format(fanart_count) if fanart_count else 'fanart'
                art[k] = _first_image_url(art_type[tr]) + fullsize
                fanart_count += 1
            if pr:
                art['keyart'] = _first_image_url(art_type[pr]) + bannersize

        elif name in ('title_treatment', 'logo'):
            if cr:
                art['clearlogo'] = _first_image_url(art_type[cr]) + thumbsize

    # poster overrides thumb for episodes, so skip for eps
    if is_episode:
        art.pop('poster', None)

    return art


def _get_text(row, field, source):
    if not row:
        return None

    texts = None
    if 'text' in row:
        # api 5.1
        texts = row['text']
    elif 'texts' in row:
        # api 3.1
        texts = {}
        for data in row['texts']:
            if data['field'] not in texts:
                texts[data['field']] = {}
            texts[data['field']][data['type']] = {data['sourceEntity']: {'default': data}}

    if not texts:
        return None

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
    art = _get_art(data['series'])
    title = _get_text(data['series'], 'title', 'series')
    folder = plugin.Folder(title, fanart=art.get('fanart'))

    for row in data['seasons']['seasons']:
        if row['seasonSequenceNumber'] < 0:
            continue
        item = _parse_season(row, data['series'])
        folder.add_items(item)

    if data['extras']['videos']:
        folder.add_item(
            label = (_.EXTRAS),
            art   = art,
            path  = plugin.url_for(extras, series_id=series_id, fanart=art.get('fanart')),
            specialsort = 'bottom',
        )

    if data['related']['items']:
        folder.add_item(
            label = _.SUGGESTED,
            art   = art,
            path  = plugin.url_for(suggested, series_id=series_id),
            specialsort = 'bottom',
        )

    return folder


@plugin.route()
@plugin.pagination()
def season(season_id, title, page=1, **kwargs):
    data = api.episodes(season_id, page=page)

    folder = plugin.Folder(title)

    items = _process_rows(data['videos'], content_class='episode')
    folder.add_items(items)

    return folder, (data['meta']['page_size'] + data['meta']['offset']) < data['meta']['hits']


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
def play_trailer(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
    elif series_id:
        data = api.series_bundle(series_id)

    videos = [x for x in data['extras']['videos'] if x.get('contentType') == 'trailer']
    if not videos:
        raise PluginError(_.TRAILER_NOT_FOUND)

    return _play(videos[0]['contentId'])


@plugin.route()
def extras(family_id=None, series_id=None, **kwargs):
    if family_id:
        data = api.video_bundle(family_id)
        fanart = _get_art(data['video']).get('fanart')
    elif series_id:
        data = api.series_bundle(series_id)
        fanart = _get_art(data['series']).get('fanart')

    folder = plugin.Folder(_.EXTRAS, fanart=fanart)
    items = _process_rows(data['extras']['videos'])
    folder.add_items(items)
    return folder


@plugin.route()
def full_details(family_id=None, series_id=None, **kwargs):
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
    if api.feature_flags().get('wpnx-disney-searchOnExplore'):
        data = api.explore_search(query)
        return _process_explore(data['containers'][0]).items if data['containers'] else [], False
    else:
        log.info("Legacy search")
        data = api.search(query)
        hits = [x['hit'] for x in data['hits']]
        return _process_rows(hits), False


@plugin.route()
@plugin.login_required()
def play(family_id=None, content_id=None, **kwargs):
    return _play(family_id, content_id, **kwargs)


def _play(family_id=None, content_id=None, **kwargs):
    if KODI_VERSION > 18:
        ver_required = '2.6.0'
    else:
        ver_required = '2.4.5'

    ia = inputstream.Widevine(
        license_key = api.get_config()['services']['drm']['client']['endpoints']['widevineLicense']['href'],
        manifest_type = 'hls',
        mimetype = 'application/vnd.apple.mpegurl',
        wv_secure = is_wv_secure(),
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

    versions = video['mediaMetadata']['facets']
    has_imax = False
    for row in versions:
        if row['activeAspectRatio'] == 1.9:
            has_imax = True

    if has_imax:
        deault_ratio = settings.DEFAULT_RATIO.value

        if deault_ratio == Ratio.ASK:
            index = gui.context_menu([_.IMAX, _.WIDESCREEN])
            if index == -1:
                return
            imax = True if index == 0 else False
        else:
            imax = True if deault_ratio == Ratio.IMAX else False

        profile = api.profile()[0]
        if imax != profile['attributes']['playbackSettings']['preferImaxEnhancedVersion']:
            api.set_imax(imax)

    playback_url = video['mediaMetadata']['playbackUrls'][0]['href']
    playback_data = api.playback_data(playback_url, ia.wv_secure)

    try:
        #v6
        media_stream = playback_data['stream']['sources'][0]['complete']['url']
    except KeyError:
        #v5
        media_stream = playback_data['stream']['complete'][0]['url']

    original_language = video.get('originalLanguage') or ''
    item = _parse_video(video)
    item.update(
        path = media_stream,
        inputstream = ia,
        headers = api.session.headers,
        proxy_data = {'original_language': original_language},
    )

    milestones = video.get('milestone', [])
    item.play_next = {}
    item.play_skips = []

    if not kwargs.get(ROUTE_RESUME_TAG):
        if settings.getBool('sync_playback', False) and NO_RESUME_TAG in kwargs and playback_data['playhead']['status'] == 'PlayheadFound':
            item.resume_from = plugin.resume_from(playback_data['playhead']['position'])
            if item.resume_from == -1:
                return

    if milestones and settings.getBool('skip_recaps', False):
        recap_start = _get_milestone(milestones, 'recap_start')
        recap_end = _get_milestone(milestones, 'recap_end')
        if recap_end > recap_start:
            item.play_skips.append({'from': recap_start, 'to': recap_end})

    if milestones and settings.getBool('skip_intros', False):
        intro_start = _get_milestone(milestones, 'intro_start')
        intro_end = _get_milestone(milestones, 'intro_end')
        if intro_end > intro_start:
            item.play_skips.append({'from': intro_start, 'to': intro_end})

    if milestones and settings.getBool('skip_credits', False):
        credits_start = _get_milestone(milestones, 'up_next')
        tag_start = _get_milestone(milestones, 'tag_start')
        tag_end = _get_milestone(milestones, 'tag_end')
        item.play_skips.append({'from': credits_start, 'to': tag_start})
        if tag_end:
            item.play_skips.append({'from': tag_end, 'to': 0})

    if video['programType'] == 'episode' and settings.getBool('play_next_episode', True):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] == 'episode' and row['encodedSeriesId'] == video['encodedSeriesId']:
                item.play_next['next_file'] = _get_play_path(content_id=row['contentId'])
                break

    elif video['programType'] != 'episode' and settings.getBool('play_next_movie', False):
        data = api.up_next(video['contentId'])
        for row in data.get('items', []):
            if row['type'] == 'DmcVideo' and row['programType'] != 'episode':
                item.play_next['next_file'] = _get_play_path(content_id=row['contentId'])
                break

    if settings.getBool('sync_playback', False):
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


### EXPLORE ###
@plugin.route()
def explore_page(page_id, **kwargs):
    data = api.explore_page(page_id)
    folder = _process_explore(data)
    # flatten
    if len(folder.items) == 1:
        return plugin.redirect(folder.items[0].path)
    return folder


@plugin.route()
@plugin.pagination()
def explore_set(set_id, page=1, **kwargs):
    data = api.explore_set(set_id, page=page)
    folder = _process_explore(data)
    return folder, data['pagination']['hasMore']


@plugin.route()
def explore_season(show_id, season_id, **kwargs):
    data = api.explore_season(season_id)
    folder = _process_explore(data)

    show_data = api.explore_page(show_id)
    show_art = _get_explore_art(show_data)
    for key in show_art:
        if key != 'poster' and not folder.art.get(key):
            folder.art[key] = show_art[key]

    return folder


def _process_explore(data, watchlist=False):
    title = data['visuals'].get('title') or data['visuals'].get('name')
    folder = plugin.Folder(title, art=_get_explore_art(data))

    if 'containers' in data:
        rows = data['containers']
    elif 'items' in data:
        rows = data['items']
    else:
        rows = []

    is_show = 'seasonsAvailable' in data['visuals'].get('metastringParts', {})

    user_states = {}
    if settings.SYNC_PLAYBACK.value:
        pids = [row.get('personalization',{}).get('pid') for row in rows if row['visuals'].get('durationMs')]
        pids = [x for x in pids if x]
        if pids:
            user_states = api.explore_userstate(pids)

    items = []
    for row in rows:
        if not is_show and row['type'] == 'set':
            item = plugin.Item(
                label = row['visuals']['name'],
                art = _get_explore_art(row),
                path = plugin.url_for(explore_set, set_id=row['id']),
            )
            items.append(item)

        elif is_show and row['type'] == 'episodes':
            seasons = []
            for season in row.get('seasons', []):
                item = plugin.Item(
                    label = season['visuals']['name'],
                    info = {
                        'plot': data['visuals']['description']['medium'],
                        'tvshowtitle': title,
                        'mediatype': 'season',
                    },
                    art = _get_explore_art(season),
                    path = plugin.url_for(explore_season, show_id=data['id'], season_id=season['id']),
                )
                match = re.search('Season ([0-9]+)', season['visuals']['name'], re.IGNORECASE)
                if match:
                    item.info['season'] = int(match.group(1))
                seasons.append(item)
            items.extend(sorted(seasons, key=lambda item: item.info.get('season') or 9999, reverse=False))

        elif not is_show and row.get('actions', []):
            # MOVIE / TV SHOW / EPISODE
            item = _parse_explore(row)
            _add_progress(user_states.get(row['personalization']['pid']), item)

            if item.info.get('mediatype') in ('movie', 'tvshow'):
                if settings.SYNC_WATCHLIST.value:
                    if watchlist:
                        item.context.append((_.DELETE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(explore_delete_watchlist, deeplink_id=row['actions'][0]['deeplinkId']))))
                    else:
                        item.context.append((_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(explore_add_watchlist, deeplink_id=row['actions'][0]['deeplinkId']))))

                item.context.append((_.EXTRAS, "Container.Update({})".format(plugin.url_for(explore_extras, deeplink_id=row['actions'][0]['deeplinkId']))))
                item.context.append((_.SUGGESTED, "Container.Update({})".format(plugin.url_for(explore_suggested, deeplink_id=row['actions'][0]['deeplinkId']))))
            items.append(item)

    folder.add_items(items)
    return folder


def _parse_explore(row):
    actions = {}
    for action in row['actions']:
        actions[action['type']] = action
    playback = actions.get('playback', actions.get('browse'))

    if 'episodeTitle' in row['visuals']:
        item = plugin.Item(
            label = row['visuals']['episodeTitle'],
            info = {
                'plot': row['visuals']['description']['full'],
                'season': row['visuals']['seasonNumber'],
                'episode': row['visuals']['episodeNumber'],
                'tvshowtitle': row['visuals']['title'],
                'duration': int(row['visuals'].get('durationMs', 0) / 1000),
                'mediatype': 'episode',
            },
            art = _get_explore_art(row),
            playable = True,
            path = _get_explore_play_path(deeplink_id=playback['deeplinkId']),
        )
        return item

    meta = row['visuals'].get('metastringParts', {})

    if not meta and 'browse' in actions:
        item = plugin.Item(
            label = row['visuals']['title'],
            art = _get_explore_art(row),
            path = plugin.url_for(explore_page, page_id=actions['browse']['pageId'])
        )
        return item

    item = plugin.Item(
        label = row['visuals']['title'],
        art = _get_explore_art(row),
        info = {
            'trailer': plugin.url_for(explore_play_trailer, deeplink_id=playback['deeplinkId']),
        }
    )

    if 'description' in row['visuals']:
        item.info['plot'] = row['visuals']['description'].get('medium',  row['visuals']['description'].get('brief', row['visuals']['description']['full']))

    if 'releaseYearRange' in meta:
        item.info['year'] = meta['releaseYearRange']['startYear']

    if 'genres' in meta:
        item.info['genre'] = meta['genres']['values']

    if 'ratingInfo' in meta:
        item.info['rating'] = meta['ratingInfo']['rating']['text']

    if 'runtime' in meta:
        item.info['duration'] = int(meta['runtime']['runtimeMs'] / 1000)
        item.info['mediatype'] = 'movie'
        item.playable = True
        item.path = _get_explore_play_path(deeplink_id=playback['deeplinkId'])
    else:
        item.info['mediatype'] = 'tvshow'
        # might be trailer which does not have trailer
        if 'browse' in actions:
            item.path = plugin.url_for(explore_page, page_id=actions['browse']['pageId'])

    return item


@plugin.route()
def explore_add_watchlist(deeplink_id, **kwargs):
    with gui.busy():
        data = api.explore_page('entity-{}'.format(deeplink_id.replace('entity-', '')))
        art = _get_explore_art(data)

        if not data['personalization']['userState'].get('inWatchlist'):
            actions = {}
            for row in data['actions']:
                actions[row['type']] = row
            api.explore_watchlist('add', page_info=data['infoBlock'], action_info=actions['modifySaves']['infoBlock'])
    gui.notification(_.ADDED_WATCHLIST, heading=data['visuals']['title'], icon=art.get('poster') or art.get('thumb'))


@plugin.route()
def explore_delete_watchlist(deeplink_id, **kwargs):
    with gui.busy():
        data = api.explore_page('entity-{}'.format(deeplink_id.replace('entity-', '')))
        if data['personalization']['userState'].get('inWatchlist'):
            actions = {}
            for row in data['actions']:
                actions[row['type']] = row
            api.explore_watchlist('remove', page_info=data['infoBlock'], action_info=actions['modifySaves']['infoBlock'])
    gui.refresh()


@plugin.route()
def explore_play_trailer(deeplink_id, **kwargs):
    with gui.busy():
        data = api.explore_page('entity-{}'.format(deeplink_id.replace('entity-', '')))
        actions = {}
        for row in data['actions']:
            actions[row['type']] = row

        if 'trailer' not in actions:
            raise PluginError(_.TRAILER_NOT_FOUND)

        trailer = actions['trailer']
        item = _parse_explore(data)

        ia = inputstream.Widevine(
            license_key = api.get_config()['services']['drm']['client']['endpoints']['widevineLicense']['href'],
            manifest_type = 'hls',
            mimetype = 'application/vnd.apple.mpegurl',
            wv_secure = is_wv_secure(),
        )

        playback_data = api.explore_playback(trailer['resourceId'], ia.wv_secure)

    item.update(
        label = u"{} ({})".format(item.label, _.TRAILER),
        playable = True,
        path = playback_data['stream']['sources'][0]['complete']['url'],
        inputstream = ia,
        headers = api.session.headers,
    )
    return item


@plugin.route()
def explore_extras(deeplink_id, **kwargs):
    data = api.explore_page('entity-{}'.format(deeplink_id.replace('entity-', '')), enhanced_limit=15)
    containers = {}
    for row in data['containers']:
        containers[row['visuals']['name']] = row

    if 'EXTRAS' in containers:
        folder = _process_explore(containers['EXTRAS'])
    else:
        folder = plugin.Folder()
    folder.title = u"{} ({})".format(data['visuals']['title'], _.EXTRAS)
    return folder


@plugin.route()
def explore_suggested(deeplink_id, **kwargs):
    data = api.explore_page('entity-{}'.format(deeplink_id.replace('entity-', '')), enhanced_limit=15)
    containers = {}
    for row in data['containers']:
        containers[row['visuals']['name']] = row

    if 'SUGGESTED' in containers:
        folder = _process_explore(containers['SUGGESTED'])
    else:
        folder = plugin.Folder()
    folder.title = u"{} ({})".format(data['visuals']['title'], _.SUGGESTED)
    return folder



def _add_progress(user_state, item):
    if not user_state or not settings.SYNC_PLAYBACK.value:
        return

    if user_state['progress']['progressPercentage'] == 100:
        item.info['playcount'] = 1

    elif user_state['progress']['progressPercentage'] > 0:
        item.info['playcount'] = 0
        if 'secondsRemaining' in user_state['progress']:
            item.resume_from = int(item.info['duration'] - user_state['progress']['secondsRemaining'])
        else:
            item.resume_from = int(user_state['progress']['progressPercentage']/100.0 * item.info['duration'])


def _get_explore_art(row):
    if not row or 'artwork' not in row['visuals']:
        return {}

    is_episode = 'episodeTitle' in row['visuals']
    images = row['visuals']['artwork']['standard']
    if 'tile' in row['visuals']['artwork']:
        images['hero_tile'] = row['visuals']['artwork']['tile']['background']

    try:
        images['background'] = row['visuals']['artwork']['hero']['background']
    except KeyError:
        pass

    try:
        images['background'] = row['visuals']['artwork']['brand']['background']
    except KeyError:
        pass

    if 'network' in row['visuals']['artwork']:
        images['thumbnail'] = row['visuals']['artwork']['network']['tile']

    def _first_image_url(d):
        return 'https://disney.images.edge.bamgrid.com/ripcut-delivery/v2/variant/disney/{}'.format(d['imageId'])

    art = {}
    # don't ask for jpeg thumb; might be transparent png instead
    thumbsize = '/scale?width=800&aspectRatio=1.78'
    bannersize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'
    fullsize = '/scale?width=1440&aspectRatio=1.78&format=jpeg'

    thumb_ratios = ['1.78', '1.33', '1.00']
    poster_ratios = ['0.71', '0.75', '0.80']
    clear_ratios = ['2.00', '1.78', '3.32']
    banner_ratios = ['3.91', '3.00', '1.78']

    if is_episode:
        thumbs = ('thumbnail',)
    else:
        thumbs = ('thumbnail', 'tile')

    fanart_count = 0
    for name in images or []:
        art_type = images[name]

        tr = br = pr = ''

        for ratio in thumb_ratios:
            if ratio in art_type:
                tr = ratio
                break

        for ratio in banner_ratios:
            if ratio in art_type:
                br = ratio
                break

        for ratio in poster_ratios:
            if ratio in art_type:
                pr = ratio
                break

        for ratio in clear_ratios:
            if ratio in art_type:
                cr = ratio
                break

        if name in thumbs:
            if tr:
                art['thumb'] = _first_image_url(art_type[tr]) + thumbsize
            if pr:
                art['poster'] = _first_image_url(art_type[pr]) + thumbsize

        elif name == 'hero_tile':
            if br:
                art['banner'] = _first_image_url(art_type[br]) + bannersize

        elif name in ('hero_collection', 'background_details', 'background'):
            if tr:
                k = 'fanart{}'.format(fanart_count) if fanart_count else 'fanart'
                art[k] = _first_image_url(art_type[tr]) + fullsize
                fanart_count += 1
            if pr:
                art['keyart'] = _first_image_url(art_type[pr]) + bannersize

        elif name in ('title_treatment', 'logo'):
            if cr:
                art['clearlogo'] = _first_image_url(art_type[cr]) + thumbsize

    if is_episode:
        art.pop('poster', None)

    return art


def _get_explore_play_path(**kwargs):
    profile_id = userdata.get('profile_id')
    if profile_id:
        kwargs['profile_id'] = profile_id

    return plugin.url_for(explore_play, **kwargs)


def _get_explore_milestone(milestones, name, default=0):
    if not milestones:
        return default

    for row in milestones:
        if row['label'] == name:
            return int(row['offsetMillis'] / 1000)

    return default


@plugin.route()
@plugin.login_required()
def explore_play(deeplink_id=None, family_id=None, **kwargs):
    if KODI_VERSION > 18:
        ver_required = '2.6.0'
    else:
        ver_required = '2.4.5'

    ia = inputstream.Widevine(
        license_key = api.get_config()['services']['drm']['client']['endpoints']['widevineLicense']['href'],
        manifest_type = 'hls',
        mimetype = 'application/vnd.apple.mpegurl',
        wv_secure = is_wv_secure(),
    )
    if not ia.check() or not inputstream.require_version(ver_required):
        gui.ok(_(_.IA_VER_ERROR, kodi_ver=KODI_VERSION, ver_required=ver_required))

    if family_id:
        data = api.explore_deeplink(family_id)
    else:
        data = api.explore_deeplink(deeplink_id.replace('entity-', ''), ref_type='deeplinkId', action='playback')

    deeplink_id = data['actions'][0]['deeplinkId'].replace('entity-', '')
    resource_id = data['actions'][0]['resourceId']
    upnext_id = data['actions'][0]['upNextId']
    available_id = data['actions'][0]['availId']
    player_experience = api.explore_player_experience(available_id)
    program_type = player_experience['analytics']['programType']

    flags = []
    item = plugin.Item()
    if program_type == 'movie':
        data = api.explore_page('entity-{}'.format(deeplink_id))
        flags = [x['value'] for x in data['visuals']['metastringParts']['audioVisual']['flags']]
        item = _parse_explore(data)
    elif program_type == 'episode':
        # TODO: this is a few requests and needs regex / name matching. Ideally an api endpoint for episode details exist
        season_num = re.search('- s([0-9]{1,})e([0-9]{1,}) -', player_experience['internalTitle']).group(1)
        show = api.explore_page(data['actions'][1]['pageId'], enhanced_limit=15)

        season = None
        for row in show['containers'][0]['seasons']:
            if row['visuals']['name'].endswith(str(season_num)):
                season = row
                break

        if season:
            for row in season['items']:
                if row['actions'][0]['deeplinkId'].replace('entity-', '') == deeplink_id:
                    item = _parse_explore(row)
                    break
            else:
                data = api.explore_season(season['id'])
                for row in data['items']:
                    if row['actions'][0]['deeplinkId'].replace('entity-', '') == deeplink_id:
                        item = _parse_explore(row)
                        break

    if 'imax_enhanced' in flags:
        deault_ratio = settings.DEFAULT_RATIO.value

        if deault_ratio == Ratio.ASK:
            index = gui.context_menu([_.IMAX, _.WIDESCREEN])
            if index == -1:
                return
            imax = True if index == 0 else False
        else:
            imax = True if deault_ratio == Ratio.IMAX else False

        profile = api.profile()[0]
        if imax != profile['attributes']['playbackSettings']['preferImaxEnhancedVersion']:
            api.set_imax(imax)

    playback_data = api.explore_playback(resource_id, ia.wv_secure)

    item.update(
        playable = True,
        path = playback_data['stream']['sources'][0]['complete']['url'],
        inputstream = ia,
        headers = api.session.headers,
        proxy_data = {'original_language': player_experience.get('originalLanguage')},
    )

    item.play_skips = []
    milestones = playback_data['stream']['editorial']
    if milestones and settings.getBool('skip_recaps', False):
        recap_start = _get_explore_milestone(milestones, 'recap_start')
        recap_end = _get_explore_milestone(milestones, 'recap_end')
        if recap_end > recap_start:
            item.play_skips.append({'from': recap_start, 'to': recap_end})

    if milestones and settings.getBool('skip_intros', False):
        intro_start = _get_explore_milestone(milestones, 'intro_start')
        intro_end = _get_explore_milestone(milestones, 'intro_end')
        if intro_end > intro_start:
            item.play_skips.append({'from': intro_start, 'to': intro_end})

    if milestones and settings.getBool('skip_credits', False):
        credits_start = _get_explore_milestone(milestones, 'up_next')
        tag_start = _get_explore_milestone(milestones, 'tag_start')
        tag_end = _get_explore_milestone(milestones, 'tag_end')
        item.play_skips.append({'from': credits_start, 'to': tag_start})
        if tag_end:
            item.play_skips.append({'from': tag_end, 'to': 0})

    upnext = None
    if program_type == 'episode' and settings.getBool('play_next_episode', True):
        data = api.explore_upnext(upnext_id)
        for row in data.get('items', []):
            if row.get('type') != 'upNext' or not row.get('sequentialEpisode'):
                continue

            for action in row['item'].get('actions', []):
                if action.get('type') == 'playback':
                    upnext = action['deeplinkId']
                    break

    elif program_type == 'movie' and settings.getBool('play_next_movie', False):
        data = api.explore_upnext(upnext_id)
        for row in data.get('items', []):
            if row.get('type') != 'upNext' or row.get('sequentialEpisode'):
                continue

            for action in row['item'].get('actions', []):
                if action.get('type') == 'playback':
                    upnext = action['deeplinkId']
                    break

    if upnext:
        kwargs = {'deeplink_id': upnext}
        item.play_next = {'next_file': _get_explore_play_path(**kwargs)}

    if settings.SYNC_PLAYBACK.value:
        telemetry = playback_data['tracking']['telemetry']
        item.callback = {
            'type':'interval',
            'interval': 30,
            'callback': plugin.url_for(callback, media_id=telemetry['mediaId'], fguid=telemetry['fguid']),
        }

    return item
### END EXPLORE ###
