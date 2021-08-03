import codecs
import random
import time

import arrow
from kodi_six import xbmc

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_SUFFIX, ROUTE_LIVE_TAG, PLAY_FROM_TYPES, PLAY_FROM_ASK, PLAY_FROM_LIVE, PLAY_FROM_START, ROUTE_RESUME_TAG

from .api import API, APIError
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
        folder.add_item(label=_(_.LOGIN, _bold=True),  path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True),  path=plugin.url_for(featured))
        folder.add_item(label=_(_.SHOWS, _bold=True),  path=plugin.url_for(shows))
        folder.add_item(label=_(_.SPORTS, _bold=True), path=plugin.url_for(sports))
        folder.add_item(label=_(_.LIVE_CHANNELS, _bold=True), path=plugin.url_for(panel, id=CHANNELS_PANEL))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': userdata.get('avatar')}, info={'plot': userdata.get('profile_name')}, _kiosk=False, bookmark=False)
        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@plugin.route()
def login(**kwargs):
    if gui.yes_no(_.LOGIN_WITH, yeslabel=_.DEVICE_LINK, nolabel=_.EMAIL_PASSWORD):
        result = _device_link()
    else:
        result = _email_password()

    if not result:
        return

    _select_profile()
    gui.refresh()

def _device_link():
    start     = time.time()
    data      = api.device_code()
    monitor   = xbmc.Monitor()

    with gui.progress(_(_.DEVICE_LINK_STEPS, url=data['verification_uri'], code=data['user_code']), heading=_.DEVICE_LINK) as progress:
        while (time.time() - start) < data['expires_in']:
            for i in range(data['interval']):
                if progress.iscanceled() or monitor.waitForAbort(1):
                    return

                progress.update(int(((time.time() - start) / data['expires_in']) * 100))

            if api.device_login(data['device_code']):
                return True

def _email_password():
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username=username, password=password)
    
    return True

@plugin.route()
@plugin.login_required()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('avatar')
    userdata.delete('profile_name')
    userdata.delete('profile_id')
    gui.refresh()

@plugin.route()
def featured(**kwargs):
    folder = plugin.Folder(_.FEATURED)
    folder.add_items(_landing('home'))
    return folder

@plugin.route()
def shows(**kwargs):
    folder = plugin.Folder(_.SHOWS)
    folder.add_items(_landing('shows'))
    return folder 

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query=query, page=page)
    return _parse_contents(data.get('results', [])), data['pages'] > page

@plugin.route()
def sports(**kwargs):
    folder = plugin.Folder(_.SPORTS)

    for row in api.sport_menu():
        slug = row['url'].split('sport!')[1]

        folder.add_item(
            label = row['name'],
            path  = plugin.url_for(sport, slug=slug, title=row['name']),
            art   = {
                'thumb': SPORT_LOGO.format(row['sport']),
            },
        )

    folder.add_items(_landing('sports'))

    return folder

@plugin.route()
def sport(slug, title, **kwargs):
    folder = plugin.Folder(title)
    folder.add_items(_landing('sport', sport=slug))
    return folder

@plugin.route()
def season(show_id, season_id, title, **kwargs):
    data = api.show(show_id=show_id, season_id=season_id)
    folder = plugin.Folder(title)

    for row in data:
        if row['title'] == 'Episodes':
            folder.add_items(_parse_contents(row.get('contents', [])))

    return folder

@plugin.route()
def show(show_id, title, **kwargs):
    data = api.show(show_id=show_id)

    folder = plugin.Folder(title)

    for row in data:
        if row['title'] == 'Seasons':
            for row2 in row.get('contents', []):
                asset = row2['data']['asset']

                folder.add_item(
                    label = asset['title'],
                    art  = {
                        'thumb': _get_image(asset, 'show', 'thumb'),
                        'fanart': _get_image(asset, 'show', 'fanart'),
                    },
                    info = {
                        'plot': asset.get('description-short'),
                    },
                    path = plugin.url_for(season, show_id=show_id, season_id=asset['id'], title=asset['title']),
                )

    return folder

@plugin.route()
def panel(id, sport=None, **kwargs):
    data = api.panel(id, sport=sport)
    folder = plugin.Folder(data['title'])
    folder.add_items(_parse_contents(data.get('contents', [])))
    return folder

@plugin.route()
@plugin.login_required()
def select_profile(**kwargs):
    _select_profile()
    gui.refresh()

def _select_profile():
    profiles = api.profiles()

    options = []
    values  = []
    can_delete = []
    default = -1

    avatars = {}
    for avatar in api.profile_avatars():
        avatars[avatar['id']] = avatar['url']

    for index, profile in enumerate(profiles):
        profile['avatar'] = avatars.get(profile['avatar_id'])
        
        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': profile['avatar']}))

        if profile['id'] == userdata.get('profile_id'):
            default = index
            _set_profile(profile, notify=False)

        elif not profile['root_flag']:
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
        _add_profile(taken_names=[x['name'].lower() for x in profiles], avatars=avatars, taken_avatars=[x['avatar_id'] for x in profiles])
    else:
        _set_profile(selected)

def _set_profile(profile, notify=True):
    userdata.set('avatar', profile['avatar'])
    userdata.set('profile_name', profile['name'])
    userdata.set('profile_id', profile['id'])

    if notify:
        gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=profile['avatar'])

def _delete_profile(profiles):
    options = []
    for index, profile in enumerate(profiles):
        options.append(plugin.Item(label=profile['name'], art={'thumb': profile['avatar']}))

    index = gui.select(_.SELECT_DELETE_PROFILE, options=options, useDetails=True)
    if index < 0:
        return

    selected = profiles[index]
    if gui.yes_no(_.DELETE_PROFILE_INFO, heading=_(_.DELTE_PROFILE_HEADER, name=selected['name'])) and api.delete_profile(selected).ok:
        gui.notification(_.PROFILE_DELETED, heading=selected['name'], icon=selected['avatar'])

def _add_profile(taken_names, avatars, taken_avatars):
    ## PROFILE AVATAR ##
    options = [plugin.Item(label=_(_.RANDOM_AVATAR, _bold=True)),]
    values  = ['_random',]
    unused  = []

    for avatar_id in avatars:
        values.append(avatar_id)

        if avatar_id in taken_avatars:
            label = _.AVATAR_USED
        else:
            label = _.AVATAR_NOT_USED
            unused.append(avatar_id)
  
        options.append(plugin.Item(label=label, art={'thumb': avatars[avatar_id]}))

    index = gui.select(_.SELECT_AVATAR, options=options, useDetails=True)
    if index < 0:
        return

    avatar_id = values[index]
    if avatar_id == '_random':
        avatar_id = random.choice(unused or avatars.keys())

    ## PROFILE NAME ##
    name = ''
    while True:
        name = gui.input(_.PROFILE_NAME, default=name).strip()
        if not name:
            return

        elif name.lower() in taken_names:
            gui.notification(_(_.PROFILE_NAME_TAKEN, name=name))
            
        else:
            break

    ## ADD PROFILE ##
    profile = api.add_profile(name, avatar_id)
    profile['avatar'] = avatars[avatar_id]
    if 'message' in profile:
        raise PluginError(profile['message'])

    _set_profile(profile)

def _landing(name, sport=None):
    items = []

    for row in api.landing(name, sport=sport):
        if row['panelType'] == 'hero-carousel' and row.get('contents') and settings.getBool('show_hero_contents', True):
            items.extend(_parse_contents(row['contents']))

        elif row['panelType'] != 'hero-carousel' and 'id' in row:
            items.append(plugin.Item(
                label = row['title'],
                path  = plugin.url_for(panel, id=row['id'], sport=sport),
            ))

    return items

def _parse_contents(rows):
    items = []

    for row in rows:
        if row['contentType'] == 'video':
            items.append(_parse_video(row['data']))

        elif row['contentType'] == 'section':
            items.append(_parse_section(row['data']))

    return items

def _parse_section(row):
    # If not asset, we are probably linking directly to a sport or something..
    if 'asset' not in row or row.get('type') == 'search-icon':
        return

    asset = row['asset']

    return plugin.Item(
        label = asset['title'],
        art  = {
            'thumb': _get_image(asset, 'show', 'thumb'),
            'fanart': _get_image(asset, 'show', 'fanart'),
        },
        info = {
            'plot': asset.get('description-short'),
        },
        path = plugin.url_for(show, show_id=asset['id'], title=asset['title']),
    )

def _get_image(asset, media_type, img_type='thumb', width=None):
    if not asset.get('image-pack'):
        images    = asset.get('images') or {}
        image_url = images.get('defaultUrl')
        if not image_url:
            return None
    else:
        image_url = IMG_URL.format(asset['image-pack'])

    image_url += '?location={}&imwidth={}'

    if img_type == 'thumb':
        return image_url.format('carousel-item', width or 415)

    elif img_type == 'fanart':
        return image_url.format('hero-default', width or 1920)

def _makeTime(start=None):
    return start.to('local').format('h:mmA') if start else ''

def _makeDate(now, start=None):
    if not start:
        return ''

    if now.year == start.year:
        return start.to('local').format('DD MMM')
    else:
        return start.to('local').format('DD MMM YY')

def _makeHumanised(now, start=None):
    if not start:
        return ''

    now   = now.to('local').replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    start = start.to('local').replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    days  = (start - now).days

    if days == -1:
        return 'yesterday'
    elif days == 0:
        return 'today'
    elif days == 1:
        return 'tomorrow'
    elif days <= 7 and days >= 1:
        return start.format('dddd')
    else:
        return _makeDate(now, start)

def _parse_video(row):
    asset   = row['asset']
    display = row['contentDisplay']
    
    now      = arrow.now()
    start    = arrow.get(asset['transmissionTime'])
    precheck = start

    if 'preCheckTime' in asset:
        precheck = arrow.get(asset['preCheckTime'])
        if precheck > start:
            precheck = start

    title = display.get('heroTitle') or display['title'] or asset['title']
    if 'heroHeader' in display:
        title += ' [' + display['heroHeader'].replace('${DATE_HUMANISED}', _makeHumanised(now, start).upper()).replace('${TIME}', _makeTime(start)) + ']'
    
    item = plugin.Item(
        label = title,
        art  = {
            'thumb' : _get_image(asset, 'video', 'thumb'),
            'fanart': _get_image(asset, 'video', 'fanart'),
        },
        info = {
            'plot': display.get('description'),
            'plotoutline': display.get('description'),
            'mediatype': 'video',
        },
        playable = True,
        is_folder = False,
    )

    is_live    = False
    play_type  = settings.getEnum('live_play_type', PLAY_FROM_TYPES, default=PLAY_FROM_ASK)
    start_from = ((start - precheck).seconds)

    if start_from < 1:
        start_from = 1

    if now < start:
        is_live = True

    elif asset['assetType'] == 'live-linear':
        is_live = True
        start_from = 0
        play_type = PLAY_FROM_LIVE

    elif asset['isLive'] and asset.get('isStreaming', False):
        is_live = True

        item.context.append((_.PLAY_FROM_LIVE, "PlayMedia({})".format(
            plugin.url_for(play, id=asset['id'], play_type=PLAY_FROM_LIVE, _is_live=is_live)
        )))

        item.context.append((_.PLAY_FROM_START, "PlayMedia({})".format(
            plugin.url_for(play, id=asset['id'], start_from=start_from, play_type=PLAY_FROM_START, _is_live=is_live)
        )))

    item.path = plugin.url_for(play, id=asset['id'], start_from=start_from, play_type=play_type, _is_live=is_live)

    return item

@plugin.route()
@plugin.login_required()
def play(id, start_from=0, play_type=PLAY_FROM_LIVE, **kwargs):
    asset = api.stream(id)

    start_from = int(start_from)
    play_type  = int(play_type)
    is_live = kwargs.get(ROUTE_LIVE_TAG) == ROUTE_LIVE_SUFFIX

    streams = [asset['recommendedStream']]
    streams.extend(asset['alternativeStreams'])
    streams = [s for s in streams if s['mediaFormat'] in SUPPORTED_FORMATS]

    if not streams:
        raise PluginError(_.NO_STREAM)

    prefer_cdn = settings.getEnum('prefer_cdn', AVAILABLE_CDNS)
    prefer_format = SUPPORTED_FORMATS[0]

    if prefer_cdn == CDN_AUTO:
        prefer_cdn = AVAILABLE_CDNS[0]
        # try:
        #     data = api.use_cdn(is_live)
        #     prefer_cdn = data['useCDN']
        #     prefer_format = 'ssai-{}'.format(data['mediaFormat']) if data['ssai'] else data['mediaFormat']
        # except Exception as e:
        #     log.debug('Failed to get preferred cdn')
        #     prefer_cdn = AVAILABLE_CDNS[0]

    providers = [prefer_cdn]
    providers.extend([s['provider'] for s in streams])

    formats = [prefer_format]
    formats.extend(SUPPORTED_FORMATS)

    streams = sorted(streams, key=lambda k: (providers.index(k['provider']), formats.index(k['mediaFormat'])))
    stream = streams[0]

    log.debug('Stream CDN: {provider} | Stream Format: {mediaFormat}'.format(**stream))

    item = plugin.Item(
        path = stream['manifest']['uri'],
        headers = HEADERS,
    )

    item.headers.update({'authorization': 'Bearer {}'.format(userdata.get('access_token'))})

    if is_live and (play_type == PLAY_FROM_LIVE or (play_type == PLAY_FROM_ASK and gui.yes_no(_.PLAY_FROM, yeslabel=_.PLAY_FROM_LIVE, nolabel=_.PLAY_FROM_START))):
        play_type = PLAY_FROM_LIVE
        start_from = 0

    ## Cloudfront streams start from correct position
    if stream['provider'] == CDN_CLOUDFRONT and start_from:
        start_from = 1

    if stream['mediaFormat'] == FORMAT_DASH:
        item.inputstream = inputstream.MPD()

    elif stream['mediaFormat'] in (FORMAT_HLS_TS, FORMAT_HLS_TS_SSAI):
        force = stream['mediaFormat'] == FORMAT_HLS_TS_SSAI or (is_live and play_type == PLAY_FROM_LIVE and asset['assetType'] != 'live-linear')
        item.inputstream = inputstream.HLS(force=force, live=is_live)
        if force and not item.inputstream.check():
            raise PluginError(_.HLS_REQUIRED)

    elif stream['mediaFormat'] in (FORMAT_HLS_FMP4, FORMAT_HLS_FMP4_SSAI):
        ## No audio on ffmpeg or IA
        item.inputstream = inputstream.HLS(force=True, live=is_live)
        if not item.inputstream.check():
            raise PluginError(_.HLS_REQUIRED)

    elif stream['mediaFormat'] in (FORMAT_DRM_DASH, FORMAT_DRM_DASH_HEVC):
        item.inputstream = inputstream.Widevine(
            license_key = LICENSE_URL,
        )

    if start_from and not kwargs[ROUTE_RESUME_TAG]:
        item.resume_from = start_from

    return item

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    data  = api.panel(CHANNELS_PANEL)
    
    try: chnos = Session().get(CHNO_URL).json()
    except: chnos = {}

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U\n')

        for row in data.get('contents', []):
            asset = row['data']['asset']

            if row['contentType'] != 'video':
                continue

            chid = asset['id']
            chno = chnos.get(chid) or ''

            f.write(u'#EXTINF:-1 tvg-id="{id}" tvg-chno="{channel}" channel-id="{channel}" tvg-logo="{logo}",{name}\n{path}\n'.format(
                id=chid, channel=chno, logo=_get_image(asset, 'video', 'thumb'), 
                    name=asset['title'], path=plugin.url_for(play, id=chid, play_type=PLAY_FROM_START, _is_live=True)))
