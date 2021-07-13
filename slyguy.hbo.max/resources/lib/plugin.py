import os
from xml.dom.minidom import parseString

from kodi_six import xbmc, xbmcplugin
from slyguy import plugin, gui, userdata, signals, inputstream, settings
from slyguy.session import Session
from slyguy.util import cenc_init
from slyguy.constants import ADDON_PROFILE

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
        folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:home', label=_.FEATURED))
        folder.add_item(label=_(_.SERIES, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:series', label=_.SERIES))
        folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:movies', label=_.MOVIES))
        folder.add_item(label=_(_.ORIGINALS, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:originals', label=_.ORIGINALS))
        folder.add_item(label=_(_.JUST_ADDED, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:just-added', label=_.JUST_ADDED))
        folder.add_item(label=_(_.LAST_CHANCE, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:last-chance', label=_.LAST_CHANCE))
        folder.add_item(label=_(_.COMING_SOON, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:coming-soon', label=_.COMING_SOON))
        folder.add_item(label=_(_.TRENDING_NOW, _bold=True), path=plugin.url_for(page, slug='urn:hbo:page:trending', label=_.TRENDING_NOW))

        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

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

    for row in rows:
        viewable = row.get('viewable') or ''
        content_type = row.get('contentType')

        if content_type in ('FEATURE', 'EXTRA'):
            items.append(plugin.Item(
                label    = row['titles']['full'],
                art      = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                info     = {
                    'duration': row['duration'],
                    'mediatype': 'movie' if content_type == 'FEATURE' else 'video',
                },
                context  = ((_.INFORMATION, 'RunPlugin({})'.format(plugin.url_for(information, slug=row['viewable']))),),
                playable = True,
                path     = _get_play_path(row['viewable']),
            ))

        elif content_type == 'SERIES':
            items.append(plugin.Item(
                label   = row['titles']['full'],
                art     = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                context = ((_.INFORMATION, 'RunPlugin({})'.format(plugin.url_for(information, slug=row['viewable']))),),
                info    = {'mediatype': 'tvshow'},
                path    = plugin.url_for(series, slug=row['viewable']),
            ))

        elif viewable.startswith('urn:hbo:franchise'):
            items.append(plugin.Item(
                label = row['titles']['full'],
                art   = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                path  = plugin.url_for(series, slug='urn:hbo:series:'+row['images']['tile'].split('/')[4]),
            ))

        elif content_type in ('SERIES_EPISODE', 'MINISERIES_EPISODE'):
            items.append(plugin.Item(
                label    = row['titles']['full'],
                art      = {'thumb': _image(row['images'].get('tileburnedin')), 'fanart':  _image(row['images'].get('tile'), size='1920x1080')},
                info     = {
                    'duration': row['duration'],
                    'tvshowtitle': row['seriesTitles']['full'],
                    'season': row.get('seasonNumber', 1),
                    'episode': row.get('numberInSeason', row.get('numberInSeries', 1)),
                    'mediatype': 'episode',
                },
                context  = ((_.GO_TO_SERIES, 'Container.Update({})'.format(plugin.url_for(series, slug=row['series']))),),
                playable = True,
                path     = _get_play_path(row['viewable']),
            ))

        elif row['id'].startswith('urn:hbo:themed-tray') and row['items']:
            items.append(plugin.Item(
                label = row['summary']['title'],
                info  = {'plot': row['summary']['description']},
                path  = plugin.url_for(page, slug=slug, label=row['summary']['title'], tab=row['id']),
            ))

        elif row['id'].startswith('urn:hbo:tray') and row['items']:
            items.append(plugin.Item(
                label = row['header']['label'],
                path  = plugin.url_for(page, slug=slug, label=row['header']['label'], tab=row['id']),
            ))

        # elif row['id'].startswith('urn:hbo:highlight'):
        #     print(row)
        #     raise

        elif row['id'].startswith('urn:hbo:tab-group'):
            for tab in row['tabs']:
                if tab['items']:
                    items.append(plugin.Item(
                        label = tab['label'],
                        path  = plugin.url_for(page, slug=slug, label=tab['label'], tab=tab['id']),
                    ))

        elif row['id'].startswith('urn:hbo:grid'):
            items.extend(_process_rows(row['items'], slug))

    return items

@plugin.route()
def information(slug, **kwargs):
    content = api.content(slug)

    if ':series' in slug:
        try:
            year = content['seasons'][0]['episodes'][0]['releaseYear']
        except:
            year = None

        item = plugin.Item(
            label = content['titles']['full'],
            art   = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':_image(content['images'].get('tile'), size='1920x1080')},
            info  = {
                'plot': content['summaries']['full'],
                'year': year,
                'tvshowtitle': content['titles']['full'],
                'mediatype': 'tvshow',
            },
            #path = plugin.url_for(series, slug=slug), #kodi stalls when trying to browse from this dialog
        )

    elif ':feature' in slug:
        item = plugin.Item(
            label = content['titles']['full'],
            art   = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':_image(content['images'].get('tile'), size='1920x1080')},
            info  = {
                'plot': content['summaries']['full'],
                'duration': content['duration'],
                'year': content['releaseYear'],
                'mediatype': 'movie',
            },
            #path = _get_play_path(slug), #kodi stalls when trying to play from this dialog
            #playable = True,
        )

    gui.info(item)

@plugin.route()
def page(slug, label, tab=None, **kwargs):
    folder = plugin.Folder(label)

    data = api.content(slug, tab=tab)
    items = _process_rows(data['items'], slug)
    folder.add_items(items)

    return folder

@plugin.route()
def series(slug, season=None, **kwargs):
    data = api.content(slug, tab=season)

    if len(data['seasons']) > 1:
        folder = plugin.Folder(data['titles']['full'], fanart=_image(data['images'].get('tile'), size='1920x1080'))

        for row in data['seasons']:
            folder.add_item(
                label = row['titles']['full'],
                info  = {
                    'plot': row['summaries']['short'],
                    'mediatype' : 'season'
                },
                art   = {'thumb': _image(data['images'].get('tileburnedin'))},
                path  = plugin.url_for(series, slug=slug, season=row['id']),
            )
    else:
        folder = plugin.Folder(data['titles']['full'], fanart=_image(data['images'].get('tile'), size='1920x1080'),
            sort_methods=[xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED])

        for row in data['episodes']:
            folder.add_item(
                label    = row['titles']['full'],
                art      = {'thumb': _image(row['images'].get('tileburnedin'))},
                info     = {
                    'plot': row['summaries']['short'],
                    'duration': row['duration'],
                    'tvshowtitle': row['seriesTitles']['full'],
                    'season': row.get('seasonNumber', 1),
                    'episode': row.get('numberInSeason', row.get('numberInSeries', 1)),
                    'mediatype': 'episode'
                },
                path     = _get_play_path(row['id']),
                playable = True,
            )

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
def search(query=None, **kwargs):
    if not query:
        query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
        if not query:
            return

        userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))

    data = api.search(query)
    if data:
        items = _process_rows(data['items'], 'search')
        folder.add_items(items)

    return folder

@plugin.route()
def login(**kwargs):
    if not _device_link():
        return

    _select_profile()
    gui.refresh()

def _device_link():
    monitor = xbmc.Monitor()
    serial, code = api.device_code()
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=code), heading=_.DEVICE_LINK) as progress:
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
        'profile_id': userdata.get('profile', {}).get('id', ''),
    }

    if settings.getBool('hbo_sync', False):
        kwargs['sync'] = 1

    return plugin.url_for(play, **kwargs)

@plugin.route()
@plugin.plugin_callback()
def mpd_request(_data, _data_path, **kwargs):
    data = _data.decode('utf8')

    data = data.replace('_xmlns:cenc', 'xmlns:cenc')
    data = data.replace('_:default_KID', 'cenc:default_KID')
    data = data.replace('<pssh', '<cenc:pssh')
    data = data.replace('</pssh>', '</cenc:pssh>')

    root = parseString(data.encode('utf8'))

    wv_secure = settings.getBool('wv_secure')
    if not wv_secure:
        for adap_set in root.getElementsByTagName('AdaptationSet'):
            height = int(adap_set.getAttribute('maxHeight') or 0)
            width = int(adap_set.getAttribute('maxWidth') or 0)

            if height >= 720:
                parent = adap_set.parentNode
                parent.removeChild(adap_set)

    dolby_vison = settings.getBool('dolby_vision', False)
    h265        = settings.getBool('h265', False)
    enable_4k   = settings.getBool('4k_enabled', True)
    enable_ac3  = settings.getBool('ac3_enabled', False)
    enable_ec3  = settings.getBool('ec3_enabled', False)
    enable_accessibility = settings.getBool('accessibility_enabled', False)

    for elem in root.getElementsByTagName('Representation'):
        parent = elem.parentNode
        codecs = elem.getAttribute('codecs').lower()
        height = int(elem.getAttribute('height') or 0)
        width = int(elem.getAttribute('width') or 0)

        if not dolby_vison and codecs.startswith('dvh1'):
            parent.removeChild(elem)

        elif not h265 and (codecs.startswith('hvc') or codecs.startswith('hev')):
            parent.removeChild(elem)

        elif not enable_4k and (height > 1080 or width > 1920):
            parent.removeChild(elem)

        elif not enable_ac3 and codecs == 'ac-3':
            parent.removeChild(elem)

        elif not enable_ec3 and codecs == 'ec-3':
            parent.removeChild(elem)

    for adap_set in root.getElementsByTagName('AdaptationSet'):
        if not adap_set.getElementsByTagName('Representation') or \
            (not enable_accessibility and adap_set.getElementsByTagName('Accessibility')):
            adap_set.parentNode.removeChild(adap_set)

    ## do below to convert all to cenc0 to work on firestick
    cenc_data = ''
    for elem in root.getElementsByTagName('ContentProtection'):
        default_kid = elem.getAttribute('cenc:default_KID').replace('-','').replace(' ','')
        if default_kid and default_kid not in cenc_data:
            cenc_data += '1210' + default_kid

    new_cenc = cenc_init(bytearray.fromhex(cenc_data))
    for elem in root.getElementsByTagName('cenc:pssh'):
        elem.firstChild.nodeValue = new_cenc

    with open(_data_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))

    return _data_path

@plugin.route()
def play(slug, **kwargs):
    data, content = api.play(slug)

    headers = {
        'Authorization': 'Bearer {}'.format(userdata.get('access_token')),
    }

    item = plugin.Item(
        path = data['url'],
        inputstream = inputstream.MPD(),
        headers = headers,
    )

    if 'drm' in data:
        item.inputstream = inputstream.Widevine(license_key = data['drm']['licenseUrl'])
        item.proxy_data['manifest_middleware'] = plugin.url_for(mpd_request)
        if settings.getBool('wv_secure'):
            item.inputstream.properties['license_flags'] = 'force_secure_decoder'

    item.play_next = {}
    if ':episode' in slug:
        item.update(
            label = content['titles']['full'],
            art   = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':  _image(content['images'].get('tile'), size='1920x1080')},
            info  = {
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
            art   = {'thumb': _image(content['images'].get('tileburnedin')), 'fanart':_image(content['images'].get('tile'), size='1920x1080')},
            info  = {
                'plot': content['summaries']['short'],
                'duration': content['duration'],
                'year': content['releaseYear'],
                'mediatype': 'movie',
            },
        )

        if settings.getBool('play_next_movie', False):
            for slug in content.get('similars', []):
                if ':feature' in slug:
                    item.play_next['next_file'] = 'urn:hbo:feature:' + slug.split(':')[3]
                    break

    if not settings.getBool('ignore_subs'):
        for row in data.get('textTracks', []):
            item.subtitles.append([row['url'], row['language']])

    return item

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    userdata.delete('profile')
    gui.refresh()
