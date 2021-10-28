import os
from xml.dom.minidom import parseString

from kodi_six import xbmc, xbmcplugin
from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.session import Session
from slyguy.util import replace_kids
from slyguy.constants import ADDON_PROFILE, MIDDLEWARE_PLUGIN
from slyguy.drm import is_wv_secure
from slyguy.log import log

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
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login), bookmark=False)
    else:
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:home', label=_.FEATURED))
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:series', label=_.SERIES))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:movies', label=_.MOVIES))
        folder.add_item(label=_(_.ORIGINALS, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:originals', label=_.ORIGINALS))
        folder.add_item(label=_(_.JUST_ADDED, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:just-added', label=_.JUST_ADDED))
        folder.add_item(label=_(_.LAST_CHANCE, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:last-chance', label=_.LAST_CHANCE))
        folder.add_item(label=_(_.COMING_SOON, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:coming-soon', label=_.COMING_SOON))
        folder.add_item(label=_(_.TRENDING_NOW, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:trending', label=_.TRENDING_NOW))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('sync_watchlist', False):
            folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(watchlist))

        if settings.getBool('sync_playback', False):
            folder.add_item(label=_(_.CONTINUE_WATCHING, _bold=True), path=plugin.url_for(continue_watching))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            profile = userdata.get('profile', {})
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': profile.get('avatar')}, info={'plot': profile.get('name')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _process_rows(rows, slug):
    items = []
    sync_watchlist = settings.getBool('sync_watchlist', False)

    for row in rows:
        viewable = row.get('viewable') or ''
        content_type = row.get('contentType')
        item = None

        if viewable.startswith('urn:hbo:franchise'):
            content_type = 'SERIES'
            viewable = 'urn:hbo:series:'+row['images']['tile'].split('/')[4]

        if content_type in ('FEATURE', 'EXTRA'):
            item = plugin.Item(
                label = row['titles']['full'],
                art = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                info = {
                    'duration': row['duration'],
                    'mediatype': 'movie' if content_type == 'FEATURE' else 'video',
                },
                context = (
                    (_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, slug=viewable))),
                    (_.EXTRAS, 'Container.Update({})'.format(plugin.url_for(extras, slug=viewable))),
                ),
                playable = True,
                path = _get_play_path(viewable),
            )

        elif content_type == 'SERIES':
            item = plugin.Item(
                label = row['titles']['full'],
                art = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                context = ((_.FULL_DETAILS, 'RunPlugin({})'.format(plugin.url_for(full_details, slug=viewable))),),
                info = {'mediatype': 'tvshow'},
                path = plugin.url_for(series, slug=viewable),
            )

        elif content_type in ('SERIES_EPISODE', 'MINISERIES_EPISODE'):
            item = plugin.Item(
                label = row['titles']['full'],
                art = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                info = {
                    'duration': row['duration'],
                    'tvshowtitle': row['seriesTitles']['full'],
                    'season': row.get('seasonNumber', 1),
                    'episode': row.get('numberInSeason', row.get('numberInSeries', 1)),
                    'mediatype': 'episode',
                },
                context = ((_.GO_TO_SERIES, 'Container.Update({})'.format(plugin.url_for(series, slug=row['series']))),),
                playable = True,
                path = _get_play_path(viewable),
            )

        elif row['id'].startswith('urn:hbo:themed-tray') and row['items']:
            item = plugin.Item(
                label = row['summary']['title'],
                info = {'plot': row['summary']['description']},
                path = plugin.url_for(page, slug=slug, label=row['summary']['title'], tab=row['id']),
            )

        elif row['id'].startswith('urn:hbo:tray') and row['items']:
            if 'header' not in row:
                continue

            item = plugin.Item(
                label = row['header']['label'],
                path = plugin.url_for(page, slug=slug, label=row['header']['label'], tab=row['id']),
            )

        # elif row['id'].startswith('urn:hbo:highlight'):
        #     print(row)
        #     raise

        elif row['id'].startswith('urn:hbo:tab-group'):
            for tab in row['tabs']:
                if tab['items']:
                    items.append(plugin.Item(
                        label = tab['label'],
                        path = plugin.url_for(page, slug=slug, label=tab['label'], tab=tab['id']),
                    ))

        elif row['id'].startswith('urn:hbo:grid'):
            items.extend(_process_rows(row['items'], slug))

        if not item:
            continue

        if row.get('viewable'):
            if slug == 'watchlist':
                item.context.insert(0, ((_.REMOVE_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(remove_watchlist, slug=row['viewable'])))))
            elif sync_watchlist:
                item.context.insert(0, ((_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, slug=row['viewable'], title=item.label, icon=item.art.get('thumb'))))))

        items.append(item)

    return items

@plugin.route()
def watchlist(**kwargs):
    folder = plugin.Folder(_.WATCHLIST)

    rows = api.watchlist()
    items = _process_rows(rows, 'watchlist')
    folder.add_items(items)

    return folder

@plugin.route()
def add_watchlist(slug, title=None, icon=None, **kwargs):
    gui.notification(_.ADDED_WATCHLIST, heading=title, icon=icon)
    api.add_watchlist(slug)

@plugin.route()
def remove_watchlist(slug, **kwargs):
    api.delete_watchlist(slug)
    gui.refresh()

@plugin.route()
def continue_watching(**kwargs):
    folder = plugin.Folder(_.CONTINUE_WATCHING)
    data = api.continue_watching()
    items = _process_rows(data['items'], 'continue_watching')
    folder.add_items(items)
    return folder

@plugin.route()
def extras(slug, **kwargs):
    content = api.express_content(slug)
    folder = plugin.Folder(_.EXTRAS, fanart=_image(content['images'].get('tile'), size='1920x1080'))

    for row in content['extras']:
        if row['extraType'] != 'code':
            continue

        folder.add_item(
            label = row['titles']['full'],
            art = {'thumb': _image(row['images'].get('tileburnedin')),},
            info = {
                'plot': row['summaries']['short'],
                'duration': row['duration'],
                'mediatype': 'video',
            },
            playable = True,
            path = _get_play_path(row['id']),
        )

    return folder

@plugin.route()
def full_details(slug, **kwargs):
    data = api.express_content(slug)

    if ':series' in slug:
        try: year = data['seasons'][0]['episodes'][0]['releaseYear']
        except: year = None

        item = plugin.Item(
            label = data['titles']['full'],
            art = {'thumb': _image(data['images'].get('tileburnedin')), 'fanart':_image(data['images'].get('tile'), size='1920x1080')},
            info = {
                'plot': data['summaries']['full'],
                'year': year,
                'tvshowtitle': data['titles']['full'],
                'mediatype': 'tvshow',
            },
            #path = plugin.url_for(series, slug=slug), #kodi stalls when trying to browse from this dialog
        )

    elif ':feature' in slug:
        item = plugin.Item(
            label = data['titles']['full'],
            art   = {'thumb': _image(data['images'].get('tileburnedin')), 'fanart':_image(data['images'].get('tile'), size='1920x1080')},
            info  = {
                'plot': data['summaries']['full'],
                'duration': data['duration'],
                'year': data['releaseYear'],
                'mediatype': 'movie',
            },
            #path = _get_play_path(slug), #kodi stalls when trying to play from this dialog
            #playable = True,
        )

    gui.info(item)

@plugin.route()
def page(slug, label, tab=None, **kwargs):
    folder = plugin.Folder(label)

    data = api.express_content(slug, tab=tab)
    items = _process_rows(data['items'], slug)
    folder.add_items(items)

    return folder

@plugin.route()
def series(slug, season=None, **kwargs):
    data = api.express_content(slug, tab=season)
    sync_watchlist = settings.getBool('sync_watchlist', False)

    if len(data['seasons']) > 1:
        folder = plugin.Folder(data['titles']['full'], fanart=_image(data['images'].get('tile'), size='1920x1080'))

        for row in data['seasons']:
            folder.add_item(
                label = row['titles']['full'],
                info = {
                    'plot': row['summaries']['short'],
                    'mediatype': 'season',
                },
                art = {'thumb': _image(data['images'].get('tileburnedin'))},
                path = plugin.url_for(series, slug=slug, season=row['id']),
            )
    else:
        folder = plugin.Folder(data['titles']['full'], fanart=_image(data['images'].get('tile'), size='1920x1080'),
            sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])

        for row in data['episodes']:
            item = plugin.Item(
                label = row['titles']['full'],
                art = {'thumb': _image(row['images'].get('tileburnedin'))},
                info = {
                    'plot': row['summaries']['short'],
                    'duration': row['duration'],
                    'tvshowtitle': row['seriesTitles']['full'],
                    'season': row.get('seasonNumber', 1),
                    'episode': row.get('numberInSeason', row.get('numberInSeries', 1)),
                    'mediatype': 'episode',
                },
                path = _get_play_path(row['id']),
                playable = True,
            )
            if sync_watchlist:
                item.context.insert(0, ((_.ADD_WATCHLIST, 'RunPlugin({})'.format(plugin.url_for(add_watchlist, slug=row['id'], title=item.label, icon=item.art.get('thumb'))))))

            folder.add_items(item)

    return folder

def _image(url, size='360x203', protection=False):
    if not url:
        return None

    replaces = {
        'size': size,
        'compression': 'low',
        'protection': 'false' if not protection else 'true',
        'scaleDownToFit': 'false',
    }

    for key in replaces:
        url = url.replace('{{{{{}}}}}'.format(key), replaces[key])

    return url

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query)
    return _process_rows(data['items'], 'search') if data else [], False

@plugin.route()
def login(**kwargs):
    if not _device_code():
        return

    _select_profile()
    gui.refresh()

def _device_code():
    monitor = xbmc.Monitor()
    serial, code = api.device_code()
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=code, url=DEVICE_CODE_URL), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int((i / float(timeout)) * 100))

            if i % 5 == 0 and api.device_login(serial, code):
                return True

@plugin.route()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()

def _avatar(profile, download=False):
    _type = profile.get('avatarImageType')

    if _type == 'user-upload':
        url = api.url('gateway', UPLOAD_AVATAR.format(image_id=profile['avatarImageId'], token=userdata.get('access_token')))
    elif _type == 'character':
        url = api.url('artist', CHARACTER_AVATAR.format(image_id=profile['avatarImageId']))
    else:
        return None

    if not download:
        return url

    dst_path = os.path.join(ADDON_PROFILE, 'profile.png')

    try:
        Session().chunked_dl(url, dst_path)
    except:
        return None
    else:
        return dst_path

def _select_profile():
    profiles = api.profiles()

    options = []
    values  = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)
        options.append(plugin.Item(label=profile['name'], art={'thumb': _avatar(profile)}))

        if profile['isMe']:
            default = index
            _set_profile(profile, switching=False)

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return

    _set_profile(values[index])

def _set_profile(profile, switching=True):
    if switching:
        api.set_profile(profile['profileId'])

    if settings.getBool('kid_lockdown', False) and profile['profileType'] == 'child':
        userdata.set('kid_lockdown', True)

    _profile = {'id': profile['profileId'], 'name': profile['name'], 'avatar': _avatar(profile, download=switching)}
    if profile['profileType'] == 'child':
        _profile.update({
            'child': 1,
            'birth': [profile['birth']['month'], profile['birth']['year']],
        })

    userdata.set('profile', _profile)

    if switching:
        gui.notification(_.PROFILE_ACTIVATED, heading=_profile['name'], icon=_profile['avatar'])

def _get_play_path(slug):
    if not slug:
        return None

    kwargs = {
        'slug': slug,
    }

    profile_id = userdata.get('profile', {}).get('id', '')
    if profile_id:
        kwargs['profile_id'] = profile_id

    if settings.getBool('sync_playback', False):
        kwargs['_noresume'] = True

    return plugin.url_for(play, **kwargs)

@plugin.route()
@plugin.plugin_middleware()
def mpd_request(_data, _path, **kwargs):
    data = _data.decode('utf8')

    data = data.replace('_xmlns:cenc', 'xmlns:cenc')
    data = data.replace('_:default_KID', 'cenc:default_KID')
    data = data.replace('<pssh', '<cenc:pssh')
    data = data.replace('</pssh>', '</cenc:pssh>')

    root = parseString(data.encode('utf8'))

    dolby_vison = settings.getBool('dolby_vision', False)
    enable_4k = settings.getBool('4k_enabled', True)
    h265 = enable_4k or settings.getBool('h265', False)
    enable_ac3 = settings.getBool('ac3_enabled', False)
    enable_ec3 = settings.getBool('ec3_enabled', False)
    enable_atmos = settings.getBool('atmos_enabled', False)

    for adap_set in root.getElementsByTagName('AdaptationSet'):
        if int(adap_set.getAttribute('maxHeight') or 0) >= 720:
            if is_wv_secure():
                for elem in adap_set.getElementsByTagName('ContentProtection'):
                    if elem.getAttribute('schemeIdUri') == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':
                        elem.setAttribute('xmlns:widevine', 'urn:mpeg:widevine:2013')
                        wv_robust = root.createElement('widevine:license')
                        wv_robust.setAttribute('robustness_level', 'HW_SECURE_CODECS_REQUIRED')
                        elem.appendChild(wv_robust)
            else:
                adap_set.parentNode.removeChild(adap_set)
                continue

        for elem in adap_set.getElementsByTagName('Representation'):
            parent = elem.parentNode
            codecs = elem.getAttribute('codecs').lower()
            height = int(elem.getAttribute('height') or 0)
            width = int(elem.getAttribute('width') or 0)

            if not dolby_vison and (codecs.startswith('dvh1') or codecs.startswith('dvhe')):
                parent.removeChild(elem)

            elif not h265 and (codecs.startswith('hvc') or codecs.startswith('hev')):
                parent.removeChild(elem)

            elif not enable_4k and (height > 1080 or width > 1920):
                parent.removeChild(elem)

            elif not enable_ac3 and codecs == 'ac-3':
                parent.removeChild(elem)

            elif (not enable_ec3 or not enable_atmos) and codecs == 'ec-3':
                is_atmos = False
                for supelem in elem.getElementsByTagName('SupplementalProperty'):
                    if supelem.getAttribute('value') == 'JOC':
                        is_atmos = True
                        break

                if not enable_ec3 or (not enable_atmos and is_atmos):
                    parent.removeChild(elem)

    ## Remove empty adaption sets
    for adap_set in root.getElementsByTagName('AdaptationSet'):
        if not adap_set.getElementsByTagName('Representation'):
            adap_set.parentNode.removeChild(adap_set)
    #################

    ## Fix of cenc pssh to only contain kids still present
    kids = []
    for elem in root.getElementsByTagName('ContentProtection'):
        kids.append(elem.getAttribute('cenc:default_KID'))

    if kids:
        for elem in root.getElementsByTagName('ContentProtection'):
            if elem.getAttribute('schemeIdUri') == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':
                for elem2 in elem.getElementsByTagName('cenc:pssh'):
                    current_cenc = elem2.firstChild.nodeValue
                    new_cenc = replace_kids(current_cenc, kids, version0=True)
                    if current_cenc != new_cenc:
                        elem2.firstChild.nodeValue = new_cenc
                        log.debug('Dash Fix: cenc:pssh {} -> {}'.format(current_cenc, new_cenc))
    ################################################

    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

@plugin.route()
@plugin.no_error_gui()
def callback(url, cut_id, runtime, _time, **kwargs):
    api.update_marker(url, cut_id, int(runtime), int(_time))

@plugin.route()
def play(slug, **kwargs):
    data, content, edit = api.play(slug)
    if not data or not content or not edit:
        return

    headers = {
        'Authorization': 'Bearer {}'.format(userdata.get('access_token')),
    }

    # if '_noanc_ad_' not in data['url']:
    #     new_url = data['url'].replace('_ad_', '_noanc_ad_')
    #     log.debug('Manifest url changed from {} to {} (to disable embedded ads)'.format(data['url'], new_url))
    #     data['url'] = new_url

    item = plugin.Item(
        path = data['url'],
        inputstream = inputstream.MPD(),
    )

    if 'defaultAudioSelection' in data:
        item.proxy_data['default_language'] = data['defaultAudioSelection']['language']

    if 'originalAudioLanguage' in data:
        item.proxy_data['original_language'] = data['originalAudioLanguage']

    if 'drm' in data:
        item.inputstream = inputstream.Widevine(license_key=data['drm']['licenseUrl'], license_headers=headers)
        item.proxy_data['middleware'] = {data['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}}
    else:
        item.headers = headers

    if settings.getBool('sync_playback', False):
        marker = api.markers([edit['playbackMarkerId'],])
        if marker and marker['position'] < edit.get('creditsStartTime', edit['duration']-10):
            item.resume_from = plugin.resume_from(marker['position'])
            if item.resume_from == -1:
                return

    item.play_next = {}
    if settings.getBool('skip_credits', True) and 'creditsStartTime' in edit:
        item.play_next['time'] = edit['creditsStartTime']

    if ':episode' in slug:
        item.update(
            label = content['titles']['full'],
            art = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':  _image(content['images'].get('tile'), size='1920x1080')},
            info = {
                'plot': content['summaries']['short'],
                'duration': content['duration'],
                'tvshowtitle': content['seriesTitles']['full'],
                'season': content.get('seasonNumber', 1),
                'episode': content.get('numberInSeason', content.get('numberInSeries', 1)),
                'mediatype': 'episode'
            },
        )

        if settings.getBool('play_next_episode', True):
            item.play_next['next_file'] = _get_play_path(content.get('next'))

    elif ':feature' in slug:
        item.update(
            label = content['titles']['full'],
            art = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':_image(content['images'].get('tile'), size='1920x1080')},
            info = {
                'plot': content['summaries']['short'],
                'duration': edit['duration'],
                'year': content['releaseYear'],
                'mediatype': 'movie',
            },
        )

        if settings.getBool('play_next_movie', False):
            for slug in content.get('similars', []):
                if ':feature' in slug:
                    item.play_next['next_file'] = 'urn:hbo:feature:' + slug.split(':')[3]
                    break

    base_url = data['url'].rsplit('/', 1)[0]
    for row in data.get('textTracks', []):
        if 'url' not in row:
            if row['type'].lower() == 'closedcaptions':
                _type = 'sdh'
            elif row['type'].lower() == 'forced':
                _type = 'forced'
            else:
                _type = 'sub'

            row['url'] = '{base_url}/t/sub/{language}_{type}.xml'.format(base_url=base_url, language=row['language'], type=_type)
            log.debug('Generated subtitle url: {}'.format(row['url']))

        item.subtitles.append({'url': row['url'], 'language': row['language'], 'forced': _type == 'forced', 'impaired': _type == 'sdh'})

    if settings.getBool('sync_playback', False):
        item.callback = {
            'type':'interval',
            'interval': 30,
            'callback': plugin.url_for(callback, url=api.url('markers', '/markers'), cut_id=edit['playbackMarkerId'], runtime=edit['duration']),
        }

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    userdata.delete('profile')
    gui.refresh()
