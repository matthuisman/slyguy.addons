import time
import codecs
from xml.sax.saxutils import escape
from xml.dom.minidom import parseString

import arrow
from slyguy import plugin, gui, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.monitor import monitor
from slyguy.drm import is_wv_secure
from slyguy.constants import MIDDLEWARE_PLUGIN, NO_RESUME_TAG, ROUTE_RESUME_TAG, ROUTE_LIVE_TAG

from .language import _
from .api import API
from .config import Config
from .mvpd import MVPD
from .settings import settings


api = API()
config = Config()


@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    config.init()
    api.new_session(config)
    plugin.logged_in = api.logged_in


@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    if not api.logged_in:
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login))
    else:
        if config.has_home():
            folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(featured))

        folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(shows))

        if config.has_movies():
            folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(movies))

        if config.has_live_tv():
            folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))

        # if config.has_brands():
        #     folder.add_item(label=_(_.BRANDS, _bold=True), path=plugin.url_for(brands))

        # if config.has_news():
        #     folder.add_item(label=_(_.NEWS, _bold=True), path=plugin.url_for(news))

        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if config.has_profiles():
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': config.image(userdata.get('profile_img'))}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    if not config.init(fresh=True):
        raise PluginError(_.OUT_OF_REGION)

    api.new_session(config)

    options = [[_.EMAIL_PASSWORD, _email_password]]

    if config.has_device_link():
        options.append([_.DEVICE_CODE, _device_code])
    if config.has_mvpd():
        options.append([_.PARTNER_LOGIN, _partner_login])

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    if config.has_profiles():
        _select_profile()

    gui.refresh()

def _partner_login():
    mpvd = MVPD(config)

    options = []
    providers = mpvd.providers()
    for provider in providers:
        options.append(plugin.Item(label=provider['primaryName'], art={'thumb': provider['pickerLogoUrl']}))

    index = gui.select(_.SELECT_PARTNER, options=options, useDetails=True)
    if index == -1:
        return

    provider = providers[index]
    code, url = mpvd.code(provider)
    start = time.time()
    max_time = 600
    thread = mpvd.wait_login(code)

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=url, code=code), heading=_.PARTNER_LOGIN) as progress:
        while (time.time() - start) < max_time:
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int(((time.time() - start) / max_time) * 100))
            if not thread.is_alive():
                token = mpvd.authorize()
                api.mvpd_login(provider, token)
                return True

def _email_password():
    username = gui.input(_.ASK_EMAIL, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username, password)

    return True

def _device_code():
    start = time.time()
    data = api.device_code()

    poll_time = int(data['retryInterval']/1000)
    max_time = int(data['retryDuration']/1000)
    device_token = data['deviceToken']
    code = data['activationCode']

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=config.device_link_url, code=code), heading=_.DEVICE_CODE) as progress:
        while (time.time() - start) < max_time:
            for i in range(poll_time):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / max_time) * 100))

            result = api.device_login(code, device_token)
            if result:
                return True

            elif result == -1:
                return False

@plugin.route()
def select_profile(**kwargs):
    _select_profile()
    gui.refresh()

def _select_profile():
    profiles = api.user()['accountProfiles']

    values = []
    options = []
    default = -1
    for index, profile in enumerate(profiles):
        values.append(profile['id'])
        options.append(plugin.Item(label=profile['name'], art={'thumb': config.image(profile['profilePicPath'])}))
        if profile['id'] == userdata.get('profile_id'):
            default = index

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    api.set_profile(values[index])
    gui.notification(_.PROFILE_ACTIVATED, heading=userdata.get('profile_name'), icon=config.image(userdata.get('profile_img')))

def _get_play_path(**kwargs):
    profile_id = userdata.get('profile_id')
    if profile_id:
        kwargs['profile_id'] = profile_id

    if settings.getBool('sync_playback', False):
        kwargs[NO_RESUME_TAG] = True

    return plugin.url_for(play, **kwargs)

@plugin.route()
def featured(slug=None, homegroup=None, **kwargs):
    if homegroup:
        data = api.homegroup(homegroup)
        folder = plugin.Folder(data['title'])

        for row in data.get('shows', []):
            folder.add_item(
                label = row['showTitle'],
                info = {
                    'plot': row.get('about'),
                    'mediatype': 'tvshow',
                },
                art = _show_art(row['showAssets']),
                path = plugin.url_for(show, show_id=row['showId']),
            )

        return folder

    folder = plugin.Folder(_.FEATURED)

    for row in api.featured():
        if slug is None:
            if not row['apiParams'].get('name'):
                if row['model'] == 'homeShowGroup':
                    for row in api.carousel(row['apiBaseUrl'], params=row['apiParams'])['homeShowGroupSections']:
                        folder.add_item(
                            label = row['title'],
                            path = plugin.url_for(featured, homegroup=row['id']),
                        )
                continue

            if row['model'] in ('keepWatching','onnow','schedule','brands'): #TODO
                continue

            folder.add_item(
                label = row['title'],
                path = plugin.url_for(featured, slug=row['apiParams']['name']),
            )
            continue

        if slug != row['apiParams'].get('name'):
            continue

        folder.title = row['title']
        params = row['apiParams']
        params['rows'] = 20
        data = api.carousel(row['apiBaseUrl'], params=row['apiParams'])

        if row['model'] == 'brands':
            rows = data['brands']
        elif row['model'] == 'schedule':
            rows = data['listing']
        else:
            rows = data['carousel']

        for row in rows:
            if row.get('showId'):
                folder.add_item(
                    label = row['showTitle'],
                    info = {
                        'plot': row.get('about'),
                        'mediatype': 'tvshow',
                    },
                    art = _show_art(row['showAssets']),
                    path = plugin.url_for(show, show_id=row['showId']),
                )

            elif row.get('movieContent'):
                data = row['movieContent']
                folder.add_item(
                    label = data['label'].strip() or data['title'].strip(),
                    info = {
                        'plot': data.get('shortDescription', data['description']),
                        'aired': data['_airDateISO'],
                        'dateadded': data['_pubDateISO'],
                        'genre': data['genre'],
                        'duration': data['duration'],
                        'mediatype': 'movie',
                        'trailer': plugin.url_for(play, video_id=row['trailerContentId']) if row.get('trailerContentId') else None,
                    },
                    art = _movie_art(data['thumbnailSet'], row.get('movieAssets')),
                    path = _get_play_path(video_id=data['contentId']),
                    playable = True,
                )

            elif row.get('type') == 'brand':
                folder.add_item(
                    label = row['title'],
                    # info = {
                    #     'plot': row.get('about'),
                    #     'mediatype': 'tvshow',
                    # },
                    # art = _show_art(row['showAssets']),
                    # path = plugin.url_for(show, show_id=row['showId']),
                )

        break

    return folder

@plugin.route()
def movies(genre=None, title=None, page=1, **kwargs):
    folder = plugin.Folder(title or _.MOVIES)
    page = int(page)
    num_results = 50

    if genre is None:
        folder.add_item(
            label = _.POPULAR,
            path = plugin.url_for(movies, genre='popular', title=_.POPULAR),
        )

        folder.add_item(
            label = _.A_Z,
            path = plugin.url_for(movies, genre='', title=_.A_Z),
        )

        for row in api.movie_genres():
            if row['slug'] in ('popular', 'a-z'):
                continue

            folder.add_item(
                label = row['title'],
                path = plugin.url_for(movies, genre=row['slug'], title=row['title']),
            )

        return folder

    if genre == 'popular':
        data = api.trending_movies()
        data['movies'] = [x['content'] for x in data['trending'] if x['content_type'] == 'movie']
        data['numFound'] = len(data['movies'])
    else:
        data = api.movies(genre=genre, num_results=num_results, page=page)

    for row in data['movies']:
        movie = row.get('movieContent')
        if not movie:
            #Skip movies that dont have a playable video
            continue

        folder.add_item(
            label = movie['label'].strip() or movie['title'].strip(),
            info = {
                'plot': movie.get('shortDescription', movie['description']),
                'aired': movie['_airDateISO'],
                'dateadded': movie['_pubDateISO'],
                'genre': movie['genre'],
                'duration': movie['duration'],
                'mediatype': 'movie',
                'trailer': plugin.url_for(play, video_id=row['movie_trailer_id']) if row.get('movie_trailer_id') else None,
            },
            art = _movie_art(movie['thumbnailSet'], row.get('movieAssets')),
            path = _get_play_path(video_id=movie['contentId']),
            playable = True,
        )

    if data['numFound'] > num_results*page:
        folder.add_item(
            label = _(_.NEXT_PAGE, page=page+1),
            path = plugin.url_for(movies, genre=genre, title=title, page=page+1),
            specialsort = 'bottom',
        )

    return folder

@plugin.route()
def shows(group_id=None, **kwargs):
    if group_id is None:
        folder = plugin.Folder(_.SHOWS)

        for row in api.show_groups():
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(shows, group_id=row['id']),
            )

        return folder

    data = api.show_group(group_id)

    folder = plugin.Folder(data['title'])
    items = _process_shows(data['showGroupItems'])
    folder.add_items(items)

    return folder

def _process_shows(rows):
    items = []

    for row in rows:
        item = plugin.Item(
            label = row['title'],
            info = {
                'genre': row['category'],
                'mediatype': 'tvshow',
            },
            art = _show_art(row['showAssets']),
            path = plugin.url_for(show, show_id=row['showId']),
        )

        items.append(item)

    return items

@plugin.route()
def related_shows(show_id, **kwargs):
    _show = api.show(show_id)
    folder = plugin.Folder(_show['show']['results'][0]['title'])

    for row in api.related_shows(show_id):
        folder.add_item(
            label = row['relatedShowTitle'],
            info = {
                'plot': row.get('relatedShowAboutCopy'),
                'mediatype': 'tvshow',
            },
            art = _show_art(row['showAssets']),
            path = plugin.url_for(show, show_id=row['relatedShowId']),
        )

    return folder

@plugin.route()
def show(show_id, config=None, **kwargs):
    _show = api.show(show_id)
    art = _show_art(_show['showAssets'])
    folder = plugin.Folder(_show['show']['results'][0]['title'], thumb=art.get('thumb'), fanart=art.get('fanart'))
    plot = _show['show']['results'][0]['about'] + '\n\n'

    if config:
        config = api.show_config(show_id, config)
        items = _show_episodes(_show, config['sectionId'], ignore_eps=True)
        folder.add_items(items)
        return folder

    for row in api.show_menu(show_id):
        if row.get('videoConfigUniqueName'): #and row.get('hasResultsFromVideoConfig'):
            config = api.show_config(show_id, row['videoConfigUniqueName'])
            if not config:
                continue

            if config.get('display_seasons') and 'episodes' in (config.get('section_type') or '').lower():
                for row in sorted(api.seasons(show_id), key=lambda x: int(x['seasonNum'])):
                    if not row['totalCount']:
                        continue

                    folder.add_item(
                        label = _(_.SEASON, number=row['seasonNum']),
                        info = {
                            'plot': plot,
                            'mediatype': 'season',
                            'tvshowtitle': _show['show']['results'][0]['title'],
                        },
                        path = plugin.url_for(season, show_id=show_id, section=config['sectionId'], season=row['seasonNum']),
                    )
            else:
                folder.add_item(
                    label = row['title'],
                    path = plugin.url_for(show, show_id=show_id, config=row['videoConfigUniqueName']),
                    specialsort = 'bottom',
                )

        elif row['page_type'] == 'related_shows':
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(related_shows, show_id=show_id),
                specialsort = 'bottom',
            )

        elif row['page_type'] == 'channel' and row.get('currentListingsSize'):
            folder.add_item(
                label = row['title'],
                path = plugin.url_for(live_tv, channel_slug=row['channel_slug']),
                specialsort = 'bottom',
            )

    return folder

def _show_episodes(_show, section, season=None, ignore_eps=False):
    items = []

    for row in sorted(api.episodes(section, season), key=lambda x: arrow.get(x['_airDateISO']), reverse=True):
        is_live = row.get('isLive', False)

        item = plugin.Item(
            label = row['label'].strip() or row['title'].strip(),
            info = {
                'aired': row['_airDateISO'],
                'dateadded': row['_pubDateISO'],
                'plot': row['shortDescription'],
                'season': None if ignore_eps else row['seasonNum'],
                'episode': None if ignore_eps else row['episodeNum'],
                'duration': None if is_live else row['duration'] ,
                'genre': row['topLevelCategory'],
                'mediatype': 'video' if ignore_eps else 'episode',
                'tvshowtitle': _show['show']['results'][0]['title'],
            },
            art = {'thumb': config.thumbnail(row['thumbnail'])},
            path = _get_play_path(video_id=row['contentId'], _is_live=is_live),
            playable = True,
        )

        if is_live:
            item.label = _(_.LIVE, label=item.label)

        items.append(item)

    return items

@plugin.route()
def season(show_id, section, season, **kwargs):
    _show = api.show(show_id)
    art = _show_art(_show['showAssets'])

    folder = plugin.Folder(_show['show']['results'][0]['title'], fanart=art.get('fanart'))
    items = _show_episodes(_show, section, season)
    folder.add_items(items)

    return folder

@plugin.route()
def live_tv(channel_slug=None, **kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    for row in api.live_channels():
        if not row['currentListing'] or (channel_slug and row['slug'] != channel_slug):
            continue

        for listing in row['currentListing']:
            start = arrow.get(listing['startTimestamp'])
            plot = u'[{}] {}\n'.format(start.to('local').format('h:mma'), listing['title'])

            if row['upcomingListing']:
                start = arrow.get(row['upcomingListing'][0]['startTimestamp'])
                plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row['upcomingListing'][0]['title'])

            label = row['channelName'].strip()
            listing_id = None
            if row['streamType'] == 'mpx_live' and len(row['currentListing']) > 1:
                listing_id = listing['id']
                label = listing['title'].strip()
                plot = listing['description']

            folder.add_item(
                label = label,
                info = {
                    'plot': plot,
                },
                art = {'thumb': config.image(row['filePathLogoSelected'])},
                path = plugin.url_for(play_channel, slug=row['slug'], listing_id=listing_id, _is_live=True),
                playable = True,
            )

    return folder

def _show_art(assets):
    assets = assets or {}
    art = {}

    if 'filepath_show_browse_poster' in assets:
        art['thumb'] = config.image(assets['filepath_show_browse_poster'])

    if 'filepath_brand_hero' in assets:
        art['fanart'] = config.image(assets['filepath_brand_hero'], 'w1920-q80')

    return art

def _get_thumb(thumbs, _type='PosterArt', dimensions='w400'):
    if not thumbs:
        return None

    for row in thumbs:
        if row['assetType'] == _type:
            return config.thumbnail(row['url'], dimensions)

    return None

def _movie_art(thumbs, assets=None):
    assets = assets or {}

    art = {
        'thumb': _get_thumb(thumbs, 'PosterArt'),
        'fanart': _get_thumb(thumbs, 'Thumbnail', 'w1920-q80'),
    }

    if not art['thumb'] and 'filepath_movie_poster' in assets:
        art['thumb'] = config.image(assets['filepath_movie_poster'])

    if not art['fanart'] and 'filepath_movie_hero_sky' in assets:
        art['fanart'] = config.image(assets['filepath_movie_hero_sky'], 'w1920-q80')

    return art

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    items = []

    for row in api.search(query):
        if row['term_type'] == 'show':
            items.append(plugin.Item(
                label = row['title'],
                info = {
                    'mediatype': 'tvshow',
                },
                art = _show_art(row['showAssets']),
                path = plugin.url_for(show, show_id=row['show_id']),
            ))

        elif row['term_type'] == 'movie':
            if not row['videoList']['itemList']:
                #Skip movies that dont have a playable video
                continue

            data = row['videoList']['itemList'][0]
            try: aired = str(arrow.get(data['_airDate'], 'MM/DD/YY'))
            except: aired = None

            items.append(plugin.Item(
                label = data['label'].strip() or data['title'].strip(),
                info = {
                    'plot': data.get('shortDescription', data['description']),
                    'aired': aired,
                    'duration': data['duration'],
                    'mediatype': 'movie',
                    'trailer': plugin.url_for(play, video_id=row['movie_trailer_id']) if row.get('movie_trailer_id') else None,
                },
                art = _movie_art(data['thumbnailSet'], row.get('movieAssets')),
                path = _get_play_path(video_id=data['contentId']),
                playable = True,
            ))

    return items, False

# def _parse_item(row):
#     if row['mediaType'] == 'Standalone':
#         row['mediaType'] = 'Movie'
#     elif row['mediaType'] == 'Clip':
#         row['mediaType'] = 'Trailer'

#     if row['mediaType'] in ('Movie', 'Trailer'):
#         return plugin.Item(
#             label = row['title'],
#             info = {
#                 'aired': row['_airDateISO'],
#                 'dateadded': row['_pubDateISO'],
#                 'genre': row['genre'],
#                 'plot': row['shortDescription'],
#                 'duration': row['duration'],
#                 'mediatype': 'movie' if row['mediaType'] == 'Movie' else 'video',
#             },
#             art = _movie_art(row['thumbnailSet']) if row['mediaType'] == 'Movie' else {'thumb': _get_thumb(row['thumbnailSet'], 'Thumbnail')},
#         )

#     return plugin.Item()

@plugin.route()
@plugin.plugin_request()
def mpd_request(_data, _path, **kwargs):
    root = parseString(_data)

    vid_sets = []
    for adap_set in root.getElementsByTagName('AdaptationSet'):
        if adap_set.getAttribute('contentType') == 'video':
            kid = None
            for elem in adap_set.getElementsByTagName('ContentProtection'):
                _kid = elem.getAttribute('cenc:default_KID')
                if _kid:
                    kid = _kid
                    break

            vid_sets.append([int(adap_set.getAttribute('maxHeight') or 0), kid, adap_set])

    vid_sets = sorted(vid_sets, key=lambda x: x[0], reverse=True)
    if vid_sets and not is_wv_secure():
        lowest = vid_sets.pop()
        for row in vid_sets:
            if row[1] != lowest[1]:
                row[2].parentNode.removeChild(row[2])

    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

@plugin.route()
@plugin.login_required()
def play(video_id, **kwargs):
    return _play(video_id, **kwargs)

def _play(video_id, **kwargs):
    data = api.play(video_id)
    item = plugin.Item(
        path = data['url'],
        headers = config.headers,
    )

    if settings.getBool('sync_playback', False) and NO_RESUME_TAG in kwargs and not kwargs.get(ROUTE_RESUME_TAG):
        item.resume_from = plugin.resume_from(api.video(video_id)['mediaTime'])
        if item.resume_from == -1:
            return

    if data['widevine']:
        item.inputstream = inputstream.Widevine(license_key=data['license_url'])
        if data['type'] == 'DASH':
            item.proxy_data['middleware'] = {data['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}}
        else:
            item.inputstream.manifest_type = 'hls'
            item.inputstream.mimetype = 'application/vnd.apple.mpegurl'

    elif data['type'] == 'DASH':
        item.inputstream = inputstream.MPD()

    else:
        item.inputstream = inputstream.HLS(live=data.get('live', ROUTE_LIVE_TAG in kwargs))

    item.headers['authorization'] = 'Bearer {}'.format(data['license_token'])

    if settings.getBool('sync_playback', False):
        item.callback = {
            'type':'interval',
            'interval': 10,
            'callback': plugin.url_for(callback, media_id=video_id),
        }


    return item

@plugin.route()
@plugin.no_error_gui()
def callback(media_id, _time, **kwargs):
    api.update_playhead(media_id, int(_time))

@plugin.route()
@plugin.login_required()
def play_channel(slug, listing_id=None, **kwargs):
    channels = api.live_channels()

    item = None
    for row in channels:
        if row['slug'] != slug:
            continue

        url = None
        if row['dma']:
            url = row['dma']['playback_url']
        elif row['currentListing']:
            if not listing_id:
                selected = row['currentListing'][0]
            else:
                selected = None
                for listing in row['currentListing']:
                    if str(listing['id']) == listing_id:
                        selected = listing
                        break

            if selected:
                if selected['contentCANVideo'] and selected['contentCANVideo'].get('liveStreamingUrl'):
                    url = selected['contentCANVideo'].get('liveStreamingUrl')
                elif selected['streamType'] == 'mpx_live':
                    item = _play(selected['videoContentId'])
                    break

        if not url:
            raise PluginError('No url found for this channel')

        item = plugin.Item(
            label = row['channelName'],
            info = {
                'plot': row['description'],
            },
            art = {'thumb': config.image(row['filePathLogoSelected'])},
            path = url,
            inputstream = inputstream.HLS(live=True),
        )

    if not item:
        raise PluginError('Unable to find that channel')

    #item.resume_from = LIVE_HEAD
    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    config.clear()
    gui.refresh()

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(plugin.url_for(epg, output='$FILE')))

        for channel in api.live_channels():
            if not channel['currentListing'] or len(channel['currentListing']) > 1:
                continue

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                id=channel['slug'], name=channel['channelName'], logo=config.image(channel['filePathLogoSelected']),
                    url=plugin.url_for(play_channel, slug=channel['slug'], _is_live=True)))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    now = arrow.now()
    until = now.shift(days=settings.getInt('epg_days', 3))
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for channel in api.live_channels():
            if not channel['currentListing'] or len(channel['currentListing']) > 1:
                continue

            f.write(u'<channel id="{id}"></channel>'.format(id=channel['slug']))

            page = 1
            stop = now
            while stop < until:
                rows = api.epg(channel['slug'], rows=100, page=page)
                page += 1
                if not rows:
                    break

                for row in rows:
                    start = arrow.get(row['startTimestamp'])
                    stop = arrow.get(row['endTimestamp'])

                    icon = u'<icon src="{}"/>'.format(config.image(row['filePathThumb'])) if row['filePathThumb'] else ''
                    desc = u'<desc>{}</desc>'.format(escape(row['description'])) if row['description'] else ''

                    f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{desc}{icon}</programme>'.format(
                        id=channel['slug'], start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(row['title']), desc=desc, icon=icon,
                    ))

        f.write(u'</tv>')
