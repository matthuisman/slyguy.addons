import re
from xml.dom.minidom import parseString

from kodi_six import xbmc
from slyguy import plugin, gui, userdata, signals, inputstream, log, _, mem_cache
from slyguy.constants import MIDDLEWARE_PLUGIN
from slyguy.drm import is_wv_secure
from slyguy.util import replace_kids

from .api import API
from .constants import L3_MAX_HEIGHT
from .settings import settings


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
        add_menu_items(folder)
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.BOOKMARKS.value:
            folder.add_item(label=_(_.BOOKMARKS, _bold=True), path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        if not userdata.get('kid_lockdown', False):
            profile = userdata.get('profile', {})
            folder.add_item(label=_.SELECT_PROFILE, path=plugin.url_for(select_profile), art={'thumb': profile.get('avatar')}, info={'plot': profile.get('name')}, _kiosk=False, bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)
    return folder


@mem_cache.cached(60*30, key='menu_items')
def add_menu_items(folder):
    data = api.collection('web-menu-bar')
    ignore = ['search-menu-item', 'my-stuff-menu-item']
    for row in data['items']:
        if row.get('hidden') or row['collection']['name'] in ignore:
            continue

        folder.add_item(
            label = _(row['collection']['title'], _bold=True),
            path = plugin.url_for(page, route=row['collection']['items'][0]['link']['linkedContentRoutes'][0]['url'].lstrip('/'))
        )


@plugin.route()
def page(route, **kwargs):
    data = api.route(route)
    folder = plugin.Folder(data['title'])
    for row in data.get('items', []):
        if 'collection' not in row:
            continue

        if 'component' in row['collection'] and row['collection']['component'].get('id') in ('hero','tab-group'):
            folder.add_items(_process_items(row['collection'].get('items', [])))
            continue

        folder.add_item(
            label = row['collection'].get('title'),
            path = plugin.url_for(collection, id=row['collection']['id']),
        )

    return folder


@plugin.route()
@plugin.pagination()
def collection(id, page=1, **kwargs):
    data = api.collection(id, page=page)
    folder = plugin.Folder(data['title'])
    if 'items' not in data:
        return folder, False

    folder.add_items(_process_items(data['items']))
    more_pages = data['meta'].get('itemsCurrentPage', 1) < data['meta'].get('itemsTotalPages', 1)
    return folder, more_pages


@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    data = api.search(query=query, page=page)
    if 'items' not in data:
        return [], False

    more_pages = data['meta'].get('itemsCurrentPage', 1) < data['meta'].get('itemsTotalPages', 1)
    return _process_items(data['items'], from_search=True), more_pages


def _art(images, only_keys=None):
    images = {x['kind']: x for x in images if x.get('src') and x.get('kind')}
    ART_MAP = {
        'clearlogo': {'kinds': ['logo-centered', 'content-logo-monochromatic', 'logo-left'], 'url_append': '?w=600', 'valid': lambda data: data['src'].lower().endswith('png')},
        'thumb': {'kinds': ['cover-artwork-square', 'poster-with-logo', 'default', 'cover-artwork'], 'url_append': '?w=600'},
        'poster': {'kinds': ['poster-with-logo'], 'url_append': '?w=600'},
        'fanart': {'kinds': ['default', 'default-wide']},
    }
    art = {}
    for key in only_keys or ART_MAP:
        art[key] = None
        for kind in ART_MAP[key]['kinds']:
            if kind in images:
                if ART_MAP[key].get('valid', lambda x: True)(images[kind]):
                    art[key] = images[kind]['src'] + ART_MAP[key].get('url_append','')
                    break
    return art


def _process_item(row, from_search=False):
    data = row.get('show') or row.get('video') or row.get('taxonomyNode') or row.get('link') or row.get('collection')
    if not data:
        raise Exception(row)

    data['name'] = data.get('title', data['name'])
    try:
        data['name'] = re.sub(r'\([0-9]{4}\)$', '', data['name']).strip()
        data['originaltitle'] = re.sub(r'\([0-9]{4}\)$', '', data['originaltitle']).strip()
    except:
        pass

    label = data['name']
    for badge in data.get('badges', []):
        if badge['id'] == 'release-state-coming-soon':
            data['premiereDate'] = data['firstAvailableDate']
      #  label += ' [B][{}][/B]'.format(badge['displayText'])

    item = plugin.Item(
        label = label,
        info = {
            'sorttitle': data['name'],
            'originaltitle': data.get('originalName'),
            'plot': data.get('longDescription'),
            'plotoutline': data.get('description'),
            'aired': data.get('premiereDate'),
            'genre': [x['name'] for x in data.get('txGenres', [])],
        },
        art = _art(data.get('images',{})),
    )

    if data.get('primaryChannel'):
        item.info['studio'] = data['primaryChannel']['name']

    for rating in data.get('ratings', []):
        if 'mpaa' in rating['contentRatingSystem']['system'].lower():
            item.info['mpaa'] = rating['code']
            break

    if 'trailerVideo' in data:
        item.info['trailer'] = plugin.url_for(play, edit_id=data['trailerVideo']['edit']['id'])

    if data.get('showType') in ('SERIES', 'TOPICAL', 'MINISERIES'):
        item.info['mediatype'] = 'tvshow'
        item.path = plugin.url_for(series, id=data['id'])

    elif data.get('showType') in ('MOVIE', 'STANDALONE'):
        item.info['mediatype'] = 'movie'
        item.playable = True
        item.path = plugin.url_for(play, id=data['id'])

    elif data.get('videoType') == 'EPISODE': 
        item.art = _art(data['show']['images'])
        item.art.update(_art(data['images'], only_keys=('thumb','poster')))
        item.info.update({
            'mediatype': 'episode',
            'episode': data.get('episodeNumber'),
            'season': data.get('seasonNumber'),
            'tvshowtitle': data['show']['name'],
            'duration': data['edit']['duration'] / 1000,
        })

        if from_search:
            item.context.append((_.GOTO_SERIES, 'Container.Update({})'.format(plugin.url_for(series, id=data['show']['id']))))

        item.playable = True
        item.path = plugin.url_for(play, edit_id=data['edit']['id'])

    elif data.get('videoType') in ('STANDALONE_EVENT', 'CLIP', 'LIVE'):
        item.info['mediatype'] = 'video'
        item.playable = True
        item.path = plugin.url_for(play, edit_id=data['edit']['id'], _is_live=data['videoType'] == 'LIVE')

    elif row.get('collection'):
        # ignore collections without title
        if not data.get('title'):
            return None
        item.path = plugin.url_for(collection, id=row['collection']['id'])

    # elif data.get('kind') in ('genre', 'Internal Link'):
    #     #TODO
    #     return None

    else:
        log.warning("Unexpected data: {}".format(data))
        return None

    return item


def _process_items(rows, from_search=False):
    items = []
    for row in rows:
        item = _process_item(row, from_search=from_search)
        items.append(item)
    return items


@plugin.route()
def series(id, season=None, **kwargs):
    data = api.series(id)
    art = _art(data['images'])
    folder = plugin.Folder(data['name'])

    if season:
        data = api.season(id, season)
        items = _process_items(data.get('items',[]))
        folder.add_items(items)
        return folder

    for row in data.get('seasons', []):
        # ignore empty seasons
        if not 'videoCountByType' in row or not row['videoCountByType'].get('EPISODE'):
            continue

        folder.add_item(
            label = _(_.SEASON, number=row['displayName']),
            info = {
                'plot': row.get('longDescription') or data.get('longDescription'),
                'plotoutline': row.get('description') or data.get('description'),
                'mediatype': 'season',
                'season': row['seasonNumber'],
                'tvshowtitle': data['name'],
            },
            art = art,
            path = plugin.url_for(series, id=id, season=row['seasonNumber']),
        )
    return folder


@plugin.route()
def login(**kwargs):
    options = [
        [_.DEVICE_CODE, _device_code],
        [_.PROVIDER_LOGIN, lambda: _device_code(provider=True)],
    ]

    index = 0 if len(options) == 1 else gui.context_menu([x[0] for x in options])
    if index == -1 or not options[index][1]():
        return

    _select_profile()
    gui.refresh()


def _device_code(provider=False):
    monitor = xbmc.Monitor()
    url, code = api.device_code(provider)
    timeout = 600

    with gui.progress(_(_.DEVICE_LINK_STEPS, code=code, url=url), heading=_.DEVICE_CODE) as progress:
        for i in range(timeout):
            if progress.iscanceled() or monitor.waitForAbort(1):
                return

            progress.update(int((i / float(timeout)) * 100))

            if i % 5 == 0 and api.device_login():
                return True


@plugin.route()
def select_profile(**kwargs):
    if userdata.get('kid_lockdown', False):
        return

    _select_profile()
    gui.refresh()


def _select_profile():
    profiles = api.profiles()

    options = []
    values  = []
    default = -1

    for index, profile in enumerate(profiles):
        values.append(profile)

        profile['_avatar'] = profile['avatar']['avatarImage']['src']+'?w=300&f=webp'

        if profile.get('pinRestricted'):
            label = _(_.PROFILE_WITH_PIN, name=profile['profileName'])
        elif profile.get('ageRestricted'):
            label = _(_.PROFILE_KIDS, name=profile['profileName'])
        else:
            label = profile['profileName']

        options.append(plugin.Item(label=label, art={'thumb': profile['_avatar']}))

        if profile['id'] == userdata.get('profile',{}).get('id'):
            default = index
            _set_profile(profile, switching=False)

    index = gui.select(_.SELECT_PROFILE, options=options, preselect=default, useDetails=True)
    if index < 0:
        return
    _set_profile(values[index])


def _set_profile(profile, switching=True):
    if switching:
        pin = None
        if profile.get('pinRestricted'):
            pin = gui.input(_.ENTER_PIN, hide_input=True).strip()
        api.switch_profile(profile, pin=pin)

    if settings.KID_LOCKDOWN.value and profile.get('ageRestricted'):
        userdata.set('kid_lockdown', True)

    profile = {'id': profile['id'], 'name': profile['profileName'], 'avatar': profile['_avatar']}
    userdata.set('profile', profile)

    if switching:
        gui.notification(_.PROFILE_ACTIVATED, heading=profile['name'], icon=profile['avatar'])


@plugin.route()
@plugin.plugin_request()
def mpd_request(_data, _path, **kwargs):
    data = _data.decode('utf8')
    root = parseString(data.encode('utf8'))
    wv_secure = is_wv_secure()

    def fix_sub(adap_set):
        lang = adap_set.getAttribute('lang')
        _type = 'sub'
        for elem in adap_set.getElementsByTagName('Role'):
            if elem.getAttribute('schemeIdUri') == 'urn:mpeg:dash:role:2011':
                value = elem.getAttribute('value')
                if value == 'caption':
                    _type = 'cc'
                elif value == 'forced-subtitle':
                    _type = 'forced'
                break

        for repr in adap_set.getElementsByTagName('Representation'):
            segments = repr.getElementsByTagName('SegmentTemplate')
            if not segments:
                continue

            for seg in segments:
                stub = seg.getAttribute('media').split('/')[1]
                repr.removeChild(seg)

            elem = root.createElement('BaseURL')
            elem2 = root.createTextNode('t/{stub}/{lang}_{type}.vtt'.format(stub='sub' if stub.startswith('t') else stub, lang=lang, type=_type))
            elem.appendChild(elem2)
            repr.appendChild(elem)

    # remove bumpers (content without encryption)
    periods = root.getElementsByTagName('Period')
    new_periods = []
    for period in periods:
        protections = [elem for elem in period.getElementsByTagName('ContentProtection') if elem.getAttribute('schemeIdUri') == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed']
        if not protections:
            period.parentNode.removeChild(period)
        else:
            new_periods.append(period)

    # remove all except the first period
    if len(new_periods) > 1 and not settings.ENABLE_CHAPTERS.value:
        for period in new_periods[1:]:
            period.parentNode.removeChild(period)
        # duration will be wrong now so remove it
        try: new_periods[0].removeAttribute('duration')
        except: pass

    # in case of bumper removal or merge periods - remove incorrect start
    try: new_periods[0].setAttribute('start', periods[0].getAttribute('start'))
    except: pass

    for adap_set in root.getElementsByTagName('AdaptationSet'):
        if adap_set.getAttribute('contentType') == 'text':
            fix_sub(adap_set)
            continue
        elif adap_set.getAttribute('contentType') != 'video':
            continue

        # Set HDR10 flag
        for property in adap_set.getElementsByTagName('EssentialProperty'):
            if (property.getAttribute('schemeIdUri'), property.getAttribute('value')) == ('urn:mpeg:mpegB:cicp:TransferCharacteristics', '16'):
                for repr in adap_set.getElementsByTagName('Representation'):
                    repr.setAttribute('hdr', 'true')

        max_height = int(adap_set.getAttribute('maxHeight') or max(int(elem.getAttribute('height') or 0) for elem in adap_set.getElementsByTagName('Representation')))
        if max_height < L3_MAX_HEIGHT:
            continue

        protections = [elem for elem in adap_set.getElementsByTagName('ContentProtection') if elem.getAttribute('schemeIdUri') == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed']
        if not protections:
            continue

        if wv_secure:
            for elem in protections:
                elem.setAttribute('xmlns:widevine', 'urn:mpeg:widevine:2013')
                wv_robust = root.createElement('widevine:license')
                wv_robust.setAttribute('robustness_level', 'HW_SECURE_CODECS_REQUIRED')
                elem.appendChild(wv_robust)
        else:
            adap_set.parentNode.removeChild(adap_set)

    # Fix of cenc pssh to only contain kids still present
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
                        log.info('Dash Fix: cenc:pssh {} -> {}'.format(current_cenc, new_cenc))

    with open(_path, 'wb') as f:
        f.write(root.toprettyxml(encoding='utf-8'))


@plugin.route()
def play(id=None, edit_id=None, **kwargs):
    if id:
        edit_id = api.get_edit_id(id)

    data = api.play(edit_id)
    item = plugin.Item(
        path = data['manifest']['url'],
    )

    if data.get('drm'):
        item.inputstream = inputstream.Widevine(license_key = data['drm']['schemes']['widevine']['licenseUrl'])
        item.proxy_data['middleware'] = {data['manifest']['url']: {'type': MIDDLEWARE_PLUGIN, 'url': plugin.url_for(mpd_request)}}
    else:
        item.inputstream = inputstream.MPD()

    return item


@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    userdata.delete('kid_lockdown')
    userdata.delete('profile')
    gui.refresh()
