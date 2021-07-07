import codecs
from xml.sax.saxutils import escape

import arrow
from slyguy import plugin, gui, settings, userdata, signals, inputstream, mem_cache
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

@mem_cache.cached(60*5)
def _channels():
    return api.channels()

def _get_channels(channels, provider=None, query=None):
    items = []
    for channel in channels:
        if provider and provider != channel['providerDisplayName']:
            continue

        if query and query not in channel['title'].lower():
            continue

        plot = ''
        if channel['currentEpisode']:
            start = arrow.get(channel['currentEpisode']['airTime'])
            end = start.shift(minutes=channel['currentEpisode']['duration'])
            plot = u'[{} - {}]\n{}'.format(start.to('local').format('h:mma'), end.to('local').format('h:mma'), channel['currentEpisode']['title'])

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
    channels = _channels()
    providers = sorted(set([x['providerDisplayName'] for x in channels]))

    if provider is None and len(providers) > 1:
        folder = plugin.Folder(_.LIVE_TV)

        folder.add_item(
            label = _.ALL,
            path = plugin.url_for(live_tv, provider=''),
        )

        for provider in providers:
            folder.add_item(
                label = provider,
                path = plugin.url_for(live_tv, provider=provider),
            )

        return folder

    folder = plugin.Folder(provider if provider else _.LIVE_TV)
    items = _get_channels(channels, provider=provider)
    folder.add_items(items)
    return folder

@plugin.route()
def search(**kwargs):
    query = gui.input(_.SEARCH, default=userdata.get('search', '')).strip()
    if not query:
        return

    userdata.set('search', query)
    channels = _channels()

    folder = plugin.Folder(_(_.SEARCH_FOR, query=query))
    items = _get_channels(channels, query=query)
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
    mem_cache.empty()
    gui.refresh()

@plugin.route()
@plugin.merge()
@plugin.login_required()
def playlist(output, **kwargs):
    user_providers = [x.lower() for x in userdata.get('merge_providers', [])]
    if not user_providers:
        raise PluginError(_.NO_PROVIDERS)

    channels = api.channels()
    avail_providers = set([x['providerDisplayName'] for x in channels])
    providers = [x for x in avail_providers if x.lower() in user_providers]
    userdata.set('merge_providers', providers)

    if not providers:
        raise PluginError(_.NO_PROVIDERS)

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
    user_providers = [x.lower() for x in userdata.get('merge_providers', [])]
    if not user_providers:
        raise PluginError(_.NO_PROVIDERS)

    channels = api.epg()
    avail_providers = set([x['providerDisplayName'] for x in channels])
    providers = [x for x in avail_providers if x.lower() in user_providers]
    userdata.set('merge_providers', providers)

    if not providers:
        raise PluginError(_.NO_PROVIDERS)

    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for channel in channels:
            if channel['providerDisplayName'] not in providers:
                continue

            f.write(u'<channel id="{id}"></channel>'.format(id=channel['id']))

            def write_program(program):
                if not program:
                    return

                start = arrow.get(program['airTime']).to('utc')
                stop = start.shift(minutes=program['duration'])

                series = program.get('seasonNumber') or 0
                episode = program.get('episodeNumber') or 0
                icon = program.get('primaryImageUrl')
                desc = program.get('description')
                subtitle = program.get('episodeTitle')

                icon = u'<icon src="{}"/>'.format(escape(icon)) if icon else ''
                episode = u'<episode-num system="onscreen">S{}E{}</episode-num>'.format(series, episode) if series and episode else ''
                subtitle = u'<sub-title>{}</sub-title>'.format(escape(subtitle)) if subtitle else ''
                desc = u'<desc>{}</desc>'.format(escape(desc)) if desc else ''

                f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{subtitle}{icon}{episode}{desc}</programme>'.format(
                    id=channel['id'], start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(program['title']), subtitle=subtitle, episode=episode, icon=icon, desc=desc))

            write_program(channel['currentEpisode'])
            for program in channel['upcomingEpisodes']:
                write_program(program)

        f.write(u'</tv>')

@plugin.route()
@plugin.login_required()
def configure_merge(**kwargs):
    channels = api.channels()

    user_providers = [x.lower() for x in userdata.get('merge_providers', [])]
    avail_providers = sorted(set([x['providerDisplayName'] for x in channels]))

    if len(avail_providers) == 1:
        user_providers = [avail_providers[0].lower()]
        userdata.set('merge_providers', user_providers)
        return

    options = []
    preselect = []
    for index, provider in enumerate(avail_providers):
        options.append(provider)
        if provider.lower() in user_providers:
            preselect.append(index)

    indexes = gui.select(heading=_.SELECT_PROVIDERS, options=options, multi=True, preselect=preselect)
    if indexes is None:
        return

    user_providers = [avail_providers[i].lower() for i in indexes]
    userdata.set('merge_providers', user_providers)
