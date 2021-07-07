import codecs

import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.constants import LIVE_HEAD
from slyguy.exceptions import PluginError

from .api import API
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
        folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(login))
        folder.add_item(label=_(_.REGISTER, _bold=True), path=plugin.url_for(login, register=1))
    else:
        folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _get_channels(provider=None, query=None):
    channels = api.channels()

    items = []
    for channel in channels:
        if provider and provider != channel['providerDisplayName']:
            continue

        if query and query not in channel['title'].lower():
            continue

        start = arrow.get(channel['currentEpisode']['airTime'])
        end = start.shift(minutes=channel['currentEpisode']['duration'])
        plot = '[{} - {}]\n{}'.format(start.to('local').format('h:mma'), end.to('local').format('h:mma'), channel['currentEpisode']['title'])

        item = plugin.Item(
            label = channel['title'],
            info = {'plot': plot},
            art = {'thumb': channel['thumb']},
            playable = True,
            path = plugin.url_for(play, id=channel['id'], _is_live=True),
        )
        items.append(item)

    return items

@plugin.route()
def live_tv(provider=None, **kwargs):
    channels = api.channels()
    providers = sorted(set([x['providerDisplayName'] for x in channels]))

    if provider is None and len(providers) > 1:
        folder = plugin.Folder(_.LIVE_TV)

        folder.add_item(
            label = 'All',
            path = plugin.url_for(live_tv, provider=''),
        )

        for provider in sorted(set([x['providerDisplayName'] for x in channels])):
            folder.add_item(
                label = provider,
                path = plugin.url_for(live_tv, provider=provider),
            )

        return folder

    folder = plugin.Folder(provider if provider else _.LIVE_TV)
    items = _get_channels(provider=provider)
    folder.add_items(items)
    return folder

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))
    items = _get_channels(query=query)
    folder.add_items(items)
    return folder

@plugin.route()
def login(register=0, **kwargs):
    register = int(register)

    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    if register and gui.input(_.CONFIRM_PASSWORD, hide_input=True).strip() != password:
        raise PluginError(_.PASSWORD_NOT_MATCH)

    api.login(username, password, register=register)
    gui.refresh()

@plugin.route()
@plugin.login_required()
def play(id, **kwargs):
    data = api.play(id)

    headers = {}
    headers.update(HEADERS)

    drm_info = data.get('drmInfo') or {}
    cookies = data.get('cookie') or {}

    if drm_info:
        if drm_info['drmScheme'].lower() == 'widevine':
            ia = inputstream.Widevine(
                license_key = drm_info['drmLicenseUrl'],
            )
            headers.update(drm_info.get('drmKeyRequestProperties') or {})
        else:
            raise PluginError('Unsupported Stream!')
    else:
        ia = inputstream.HLS(live=True)

    return plugin.Item(
        path = data['url'],
        inputstream = ia,
        headers = headers,
        cookies = cookies,
        resume_from = LIVE_HEAD,
    )

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    channels = api.channels()

    avail_providers = [x['providerDisplayName'] for x in channels]
    user_providers = userdata.get('merge_providers', [])
    providers = [x for x in user_providers if x in avail_providers]

    if not providers:
        raise Exception(_.NO_PROVIDERS)

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for channel in channels:
            if channel['providerDisplayName'] not in providers:
                continue

            f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{provider}",{name}\n{url}'.format(
                id=channel['id'], name=channel['title'], logo=channel['thumb'], provider=channel['providerDisplayName'], url=plugin.url_for(play, id=channel['id'], _is_live=True),
            ))

@plugin.route()
@plugin.merge()
@plugin.login_required()
def epg(output, **kwargs):
    raise Exception('Not implemented yet')

@plugin.route()
@plugin.login_required()
def configure_merge(**kwargs):
    channels = api.channels()

    user_providers = userdata.get('merge_providers', [])
    avail_providers = sorted(set([x['providerDisplayName'] for x in channels]))

    if len(avail_providers) == 1:
        userdata.set('merge_providers', avail_providers)
        return

    options = []
    preselect = []
    for index, provider in enumerate(avail_providers):
        options.append(provider)
        if provider in user_providers:
            preselect.append(index)

    indexes = gui.select(heading=_.SELECT_PROVIDERS, options=options, multi=True, preselect=preselect)
    if indexes is None:
        return

    user_providers = [avail_providers[i] for i in indexes]
    userdata.set('merge_providers', user_providers)
