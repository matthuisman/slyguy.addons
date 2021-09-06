import codecs

import arrow
from kodi_six import xbmcplugin

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.log import log
from slyguy.exceptions import PluginError

from .api import API
from .language import _
from .constants import IMG_URL, TYPE_LIVE, TYPE_VOD, LIVE_SITEID, VOD_SITEID, ASSET_TVSHOW, ASSET_MOVIE, ASSET_BOTH, HEADERS, EPG_EVENTS_COUNT

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
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        folder.add_item(label=_(_.TV_SHOWS, _bold=True), path=plugin.url_for(assets, title=_.TV_SHOWS, asset_type=ASSET_TVSHOW))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(assets, title=_.MOVIES, asset_type=ASSET_MOVIE))
        folder.add_item(label=_(_.SPORTS, _bold=True), path=plugin.url_for(assets, title=_.SPORTS, _filter=5))
        folder.add_item(label=_(_.KIDS, _bold=True), path=plugin.url_for(kids))
        folder.add_item(label=_(_.RECOMMENDED, _bold=True), path=plugin.url_for(recommended))
        folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(user_catalog, catalog_name='continue-watching'))
        folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(user_catalog, catalog_name='watchlist'))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def recommended(**kwargs):
    folder = plugin.Folder(_.RECOMMENDED)
    _bundle(folder)
    return folder

@plugin.route()
def user_catalog(catalog_name, **kwargs):
    data = api.user_catalog(catalog_name)
    if not data:
        return plugin.Folder()

    folder = plugin.Folder(data['name'])

    items = _parse_elements(data['assets'], from_menu=True)
    folder.add_items(items)

    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query)
    hide_locked = settings.getBool('hide_locked')

    #total_results = data['groupCount'] #pagination
    entitlements = _get_entitlements()

    items = []
    for group in sorted(data['groups'], key=lambda d: d['score'], reverse=True):
        hitcount = int(group['hitCount'])

        for hit in group['hits']:
            meta = hit['metadata']

            try:
                channelTag = hit['relevantSchedules'][0]['feature']['channelTag']
            except:
                try:
                    channelTag = hit['relevantSchedules'][0]['channelTag']
                except:
                    channelTag = None

            meta['locked'] = entitlements and channelTag and channelTag not in entitlements
            if meta['locked'] and hide_locked:
                continue

            season = int(meta.get('seasonNumber', 0))
            episode = int(meta.get('episodeNumber', 0))

            if meta['contentType'].upper() == 'MOVIE':
                items.append(plugin.Item(
                    label = _(_.LOCKED, label=meta['title']) if meta['locked'] else meta['title'],
                    info  = {
                        'plot': meta.get('shortSynopsis'),
                    #    'duration': int(elem.get('duration') or 0),
                        'year': int(meta.get('yearOfRelease') or 0),
                        'mediatype': 'movie',
                    },
                    art = {'thumb': 'https://images1.resources.foxtel.com.au/{}?w=400'.format(hit['images']['title']['portrait'][0]['URI']), 'fanart':'https://images1.resources.foxtel.com.au/{}?w=800'.format(hit['images']['title']['landscape'][0]['URI'])},
                    playable = True,
                    path = plugin.url_for(play_program, show_id=meta['titleId'], program_id=hit['id']),
                ))
            elif hitcount <= 1 and season > 0 and episode > 0:
                label = _(_.EPISODE_MENU_TITLE, title=meta['title'], season=season, episode=episode)
                go_to_show = plugin.url_for(show, show_id=meta['titleId'])

                items.append(plugin.Item(
                    label = _(_.LOCKED, label=label) if meta['locked'] else label,
                    info  = {
                            'plot': 'S{} EP{} - {}\n\n{}'.format(season, episode, meta.get('episodeTitle', meta['title']), meta.get('shortSynopsis')),
                            'episode': episode,
                            'season': season,
                            'tvshowtitle': meta['title'],
                        #  'duration': int(elem.get('duration') or 0),
                            'year': int(meta.get('yearOfRelease') or 0),
                            'mediatype': 'episode',
                    },
                    art = {'thumb': 'https://images1.resources.foxtel.com.au/{}?w=400'.format(hit['images']['episode']['landscape'][0]['URI']), 'fanart': 'https://images1.resources.foxtel.com.au/{}?w=800'.format(hit['images']['episode']['landscape'][0]['URI'])},
                    playable = True,
                    path = plugin.url_for(play_program, show_id=meta['titleId'], program_id=hit['id']),
                    context = [(_(_.GO_TO_SHOW_CONTEXT, title=meta['title']), "Container.Update({})".format(go_to_show))],
                ))
            else:
                items.append(plugin.Item(
                    label = _(_.LOCKED, label=meta['title']) if meta['locked'] else meta['title'],
                    info  = {
                        'tvshowtitle': meta['title'],
                        'year': int(meta.get('yearOfRelease') or 0),
                        'mediatype': 'tvshow',
                    },
                    art = {'thumb': 'https://images1.resources.foxtel.com.au/{}?w=400'.format(hit['images']['default']['landscape'][0]['URI']), 'fanart': 'https://images1.resources.foxtel.com.au/{}?w=800'.format(hit['images']['default']['landscape'][0]['URI'])},
                    path = plugin.url_for(show, show_id=meta['titleId']),
                ))

    return items, False

@plugin.route()
def kids(**kwargs):
    folder = plugin.Folder(_.KIDS)
    _bundle(folder, mode='kids')
    return folder

def _bundle(folder, mode=''):
    data = api.bundle(mode=mode)

    for block in data['blocks']:
        if 'data' not in block:
            continue

        folder.add_item(
            label = block['name'],
            path = plugin.url_for(assets, title=block['name'], _filter=block['data'], menu=0),
        )

@plugin.route()
def assets(title, asset_type=ASSET_BOTH, _filter=None, menu=1, **kwargs):
    menu   = int(menu)
    folder = plugin.Folder(title)

    if menu:
        data = api.assets(asset_type, _filter, showall=False)

        def _add_menu(menuitem):
            item = plugin.Item(
                label = menuitem['text'],
                path = plugin.url_for(assets, title=title, asset_type=asset_type, _filter=menuitem['data'], menu=int(len(menuitem.get('menuItem', [])) > 0)),
            )

            folder.add_items([item])

        if not _filter:
            for menuitem in data['menu']['menuItem']:
                _add_menu(menuitem)
        else:
            for row in data['content'].get('contentGroup', []):
                item = plugin.Item(
                    label = row['name'],
                    path = plugin.url_for(assets, title=title, asset_type=asset_type, _filter=row['data'], menu=0),
                )

                folder.add_items([item])
    else:
        data = api.assets(asset_type, _filter, showall=True)

        elements = []
        for e in data['content'].get('contentGroup', []):
            elements.extend(e.get('items', []))

        items = _parse_elements(elements, from_menu=True)
        folder.add_items(items)

    return folder

def _parse_elements(elements, from_menu=False):
    entitlements = _get_entitlements()

    items = []
    for elem in elements:
        elem['locked'] = entitlements and elem['channelCode'] not in entitlements

        if elem['locked'] and settings.getBool('hide_locked'):
            continue

        if elem['type'] == 'movie':
            item = _parse_movie(elem)

        elif elem['type'] == 'episode':
            item = _parse_episode(elem, from_menu=from_menu)

        elif elem['type'] == 'show':
            item = _parse_show(elem)

        elif elem['type']  == 'series':
            log.debug('Series! You should no longer see this. Let me know if you do...')
            continue

        else:
            continue

        items.append(item)

    return items

def _parse_movie(elem):
    return plugin.Item(
        label = _(_.LOCKED, label=elem['title']) if elem['locked'] else elem['title'],
        art   = {'thumb': _image(elem['image']), 'fanart': _image(elem.get('widescreenImage', elem['image']), 600)},
        info  = {
            'plot': elem.get('synopsis'),
            'duration': int(elem.get('duration') or 0),
            'year': int(elem.get('year') or 0),
            'mediatype': 'movie',
        },
        path  = plugin.url_for(play, media_type=TYPE_VOD, id=elem.get('mediaId', elem['id'])),
        playable = True,
    )

def _parse_show(elem):
    return plugin.Item(
        label = _(_.LOCKED, label=elem['title']) if elem['locked'] else elem['title'],
        art   = {'thumb': _image(elem['image']), 'fanart': _image(elem.get('widescreenImage', elem['image']), 600)},
        info  = {
            'plot': elem.get('synopsis'),
            'tvshowtitle': elem['title'],
            'year': int(elem.get('year') or 0),
            'mediatype': 'tvshow',
        },
        path  = plugin.url_for(show, show_id=elem['showId']),
    )

def _parse_episode(elem, from_menu=False):
    context = []

    art = {'thumb': _image(elem['image'])}

    if from_menu:
        if 'subtitle'in elem:
            label = _(_.EPISODE_SUBTITLE, title=elem['title'], subtitle=elem['subtitle'].rsplit('-')[0].strip())
        elif 'season' in elem and 'episodeNumber' in elem:
            label = _(_.EPISODE_MENU_TITLE, title=elem['title'], season=elem['season'], episode=elem['episodeNumber'])
        else:
            label = elem['title'] or elem['episodeTitle']

        go_to_show = plugin.url_for(show, show_id=elem['showId'])
        context.append((_(_.GO_TO_SHOW_CONTEXT, title=elem['title']), "Container.Update({})".format(go_to_show)))

        art['fanart'] = _image(elem.get('widescreenImage', elem['image']), 600)
    else:
        label = elem['episodeTitle'] or elem['title']

    if elem['locked']:
        label = _(_.LOCKED, label=label)

    return plugin.Item(
        label = label,
        art   = art,
        info  = {
            'plot': elem.get('synopsis'),
            'episode': int(elem.get('episodeNumber') or 0),
            'season': int(elem.get('season') or 0),
            'tvshowtitle': elem['title'],
            'duration': int(elem.get('duration') or 0),
            'year': int(elem.get('year') or 0),
            'mediatype': 'episode',
        },
        path     = plugin.url_for(play, media_type=TYPE_VOD, id=elem.get('mediaId', elem['id'])),
        context  = context,
        playable = True,
    )

@plugin.route()
def show(show_id, season=None, **kwargs):
    season = season
    data   = api.show(show_id)
    folder = plugin.Folder(data['title'], fanart=_image(data.get('widescreenImage', data['image']), 600), sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])

    flatten = False
    seasons = data['childAssets']['items']
    if len(seasons) == 1 and len(seasons[0]['childAssets']['items']) == 1:
        flatten = True

    if season == None and not flatten:
        for item in seasons:
            folder.add_item(
                label =  _(_.SEASON, season_number=item['season']),
                info = {
                    'tvshowtitle': data['title'],
                    'mediatype': 'season',
                },
                path = plugin.url_for(show, show_id=show_id, season=item['season']),
                art = {'thumb': _image(data['image'])},
            )
    else:
        for item in seasons:
            if season and int(item['season']) != int(season):
                continue

            items = _parse_elements(item['childAssets']['items'])
            folder.add_items(items)

    return folder

def _get_entitlements():
    entitlements = userdata.get('entitlements')
    if not entitlements:
        return []

    return entitlements.split(',')

def _image(id, width=400, fragment=''):
    if fragment:
        fragment = '#{}'.format(fragment)
    return IMG_URL.format(id=id, width=width, fragment=fragment)

@plugin.route()
def live_tv(_filter=None, **kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    data = api.live_channels(_filter)

    if not _filter:
        for genre in data['genres']['items']:
            folder.add_item(
                label = genre['title'],
                path  = plugin.url_for(live_tv, _filter=genre['data']),
            )
    else:
        entitlements = _get_entitlements()

        show_epg = settings.getBool('show_epg', True)
        if show_epg:
            now = arrow.utcnow()
            channel_data = api.channel_data()

        channels = []
        codes = []
        for elem in sorted(data['liveChannel'], key=lambda e: e['channelId']):
            elem['locked'] = entitlements and elem['channelCode'] not in entitlements

            if elem['locked'] and settings.getBool('hide_locked'):
                continue
            else:
                channels.append(elem)
                codes.append(elem['channelCode'])

        for elem in channels:
            plot = u''
            count = 0
            if show_epg and elem['channelCode'] in channel_data:
                for index, row in enumerate(channel_data[elem['channelCode']].get('epg', [])):
                    start = arrow.get(row[0])
                    try: stop = arrow.get(channel['epg'][index+1][0])
                    except: stop = start.shift(hours=1)

                    if (now > start and now < stop) or start > now:
                        plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), row[1])
                        count += 1
                        if count == EPG_EVENTS_COUNT:
                            break

            label = _(_.CHANNEL, channel=elem['channelId'], title=elem['title'])
            if elem['locked']:
                label = _(_.LOCKED, label=label)

            folder.add_item(
                label = label,
                art = {'thumb': _image('{id}:{site_id}:CHANNEL:IMAGE'.format(id=elem['id'], site_id=LIVE_SITEID, name=elem['title']), fragment=elem['title'])},
                info = {
                    'plot': plot,
                },
                path = plugin.url_for(play, media_type=TYPE_LIVE, id=elem['id'], _is_live=True),
                playable = True,
            )

    return folder

@plugin.route()
@plugin.login_required()
def play_program(show_id, program_id, **kwargs):
    elem = api.asset_for_program(show_id, program_id)
    return _play(TYPE_VOD, elem['id'])

@plugin.route()
@plugin.login_required()
def play(media_type, id, **kwargs):
    return _play(media_type, id)

def _play(media_type, id):
    url, license_url = api.play(media_type, id)

    item = plugin.Item(
        inputstream = inputstream.Widevine(license_key=license_url),
        path = url,
        headers = HEADERS,
    )

    if media_type == TYPE_LIVE:
        item.inputstream.properties['manifest_update_parameter'] = 'full'

    return item

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
@plugin.login_required()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data = api.live_channels()
    entitlements = _get_entitlements()

    genres = {}
    for genre in data['genres']['items'][1:]: #skip first "All channels" genre
        channels = api.live_channels(_filter=genre['data'])['liveChannel']
        for channel in channels:
            genres[channel['channelCode']] = genre['title']

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for elem in sorted(data['liveChannel'], key=lambda e: e['order']):
            if entitlements and elem['channelCode'] not in entitlements:
                continue

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" channel-id="{channel}" group-title="{group}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                id=elem['channelCode'], channel=elem['channelId'], logo=_image('{id}:{site_id}:CHANNEL:IMAGE'.format(id=elem['id'], site_id=LIVE_SITEID), fragment=elem['title']),
                name=elem['title'], group=genres.get(elem['channelCode'], ''), path=plugin.url_for(play, media_type=TYPE_LIVE, id=elem['id'], _is_live=True)))
