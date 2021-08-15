import codecs
import re
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
        if not settings.getBool('hide_my_channels', False):
            folder.add_item(label=_(_.MY_CHANNELS, _bold=True), path=plugin.url_for(live_tv, provider=MY_CHANNELS))
        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

        if settings.getBool('bookmarks', True):
            folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

        folder.add_item(label=_.LOGOUT, path=plugin.url_for(logout), _kiosk=False, bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

@mem_cache.cached(60*5)
def _channels():
    return api.channels()

def _providers(channels):
    hide_public = settings.getBool('hide_public', False)
    hide_custom = settings.getBool('hide_custom', False)
    remove_numbers = settings.getBool('remove_numbers', False)

    providers = {
        ALL: {'name': _.ALL, 'channels': [], 'logo': None, 'sort': 0},
        MY_CHANNELS: {'name': _.MY_CHANNELS, 'channels': [], 'logo': None, 'sort': 0},
    }

    favourites = userdata.get('favourites') or []
    for channel in channels:
        key = channel['providerDisplayName'].lower()

        if (key == PUBLIC and hide_public) or (key == CUSTOM and hide_custom):
            continue

        if key not in providers:
            sort = 2 if key in (PUBLIC, CUSTOM) else 1
            providers[key] = {'name': channel['providerDisplayName'], 'channels': [], 'logo': PROVIDER_ART.get(key, None), 'sort': sort}

        if remove_numbers:
            channel['title'] = re.sub('^[0-9]+\.[0-9]+', '', channel['title']).strip()

        providers[key]['channels'].append(channel)
        providers[ALL]['channels'].append(channel)
        if channel['id'] in favourites:
            providers[MY_CHANNELS]['channels'].append(channel)

    if settings.getBool('hide_my_channels', False):
        providers.pop(MY_CHANNELS)

    return providers

def _process_channels(channels, query=None, provider=ALL):
    items = []
    for channel in sorted(channels, key=lambda x: x['title'].lower().strip()):
        if query and query not in channel['title'].lower():
            continue

        plot = ''
        if channel['currentEpisode']:
            start = arrow.get(channel['currentEpisode']['airTime'])
            end = start.shift(minutes=channel['currentEpisode']['duration'])
            plot += u'[{} - {}]\n{}'.format(start.to('local').format('h:mma'), end.to('local').format('h:mma'), channel['currentEpisode']['title'])

        item = plugin.Item(
            label = channel['title'],
            info = {'plot': plot},
            art = {'thumb': channel['thumb']},
            playable = True,
            path = plugin.url_for(play, id=channel['id'], _is_live=True),
            context = ((_.DEL_MY_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(del_favourite, id=channel['id']))),) if provider == MY_CHANNELS else ((_.ADD_MY_CHANNEL, 'RunPlugin({})'.format(plugin.url_for(add_favourite, id=channel['id'], name=channel['title'], icon=channel['thumb']))),),
        )
        items.append(item)

    return items

@plugin.route()
def del_favourite(id, **kwargs):
    favourites = userdata.get('favourites') or []
    if id in favourites:
        favourites.remove(id)

    userdata.set('favourites', favourites)
    gui.refresh()

@plugin.route()
def add_favourite(id, name, icon, **kwargs):
    favourites = userdata.get('favourites') or []
    if id not in favourites:
        favourites.append(id)

    userdata.set('favourites', favourites)
    gui.notification(_.MY_CHANNEL_ADDED, heading=name, icon=icon)

@plugin.route()
def live_tv(provider=None, **kwargs):
    providers = _providers(_channels())

    if len(providers) == 1:
        provider = list(providers.keys())[0]

    if not settings.getBool('show_providers', True) and provider != MY_CHANNELS:
        provider = ALL

    if provider is None:
        folder = plugin.Folder(_.LIVE_TV)

        providers.pop(MY_CHANNELS)
        for slug in sorted(providers, key=lambda x: (providers[x]['sort'], providers[x]['name'].lower())):
            provider = providers[slug]

            folder.add_item(
                label = _(u'{name} ({count})'.format(name=provider['name'], count=len(provider['channels']))),
                art = {'thumb': provider['logo']},
                path = plugin.url_for(live_tv, provider=slug),
            )

        return folder

    _provider = providers[provider]
    folder = plugin.Folder(_provider['name'])
    items = _process_channels(_provider['channels'], provider=provider)
    folder.add_items(items)
    return folder

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    provider = _providers(_channels())[ALL]
    return _process_channels(provider['channels'], query=query), False

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
        resume_from = LIVE_HEAD, ## Need to seek to live over multi-periods
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
    user_providers = userdata.get('merge_providers', [])
    if not user_providers:
        raise PluginError(_.NO_PROVIDERS)

    providers = _providers(api.channels())
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        added = []
        for key in sorted(providers, key=lambda x: (providers[x]['sort'], providers[x]['name'].lower())):
            if key not in user_providers:
                continue

            for channel in sorted(providers[key]['channels'], key=lambda x: x['title'].lower().strip()):
                if channel['id'] in added:
                    continue

                added.append(channel['id'])
                f.write(u'\n#EXTINF:-1 tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{provider}",{name}\n{url}'.format(
                    id=channel['id'], name=channel['title'], logo=channel['thumb'], provider=channel['providerDisplayName'], url=plugin.url_for(play, id=channel['id'], _is_live=True),
                ))

@plugin.route()
@plugin.merge()
@plugin.login_required()
def epg(output, **kwargs):
    user_providers = userdata.get('merge_providers', [])
    if not user_providers:
        raise PluginError(_.NO_PROVIDERS)

    now = arrow.utcnow()
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for i in range(0, settings.getInt('epg_days', 3)):
            providers = _providers(api.epg(date=now.shift(days=i)))

            for channel in providers[ALL]['channels']:
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
    user_providers = userdata.get('merge_providers', [])
    avail_providers = _providers(_channels())

    options = []
    values = []
    preselect = []

    for index, key in enumerate(sorted(avail_providers, key=lambda x: (avail_providers[x]['sort'], avail_providers[x]['name']))):
        provider = avail_providers[key]

        values.append(key)
        options.append(plugin.Item(label=provider['name'], art={'thumb': provider['logo']}))
        if key in user_providers:
            preselect.append(index)

    indexes = gui.select(heading=_.SELECT_PROVIDERS, options=options, useDetails=True, multi=True, preselect=preselect)
    if indexes is None:
        return

    user_providers = [values[i] for i in indexes]
    userdata.set('merge_providers', user_providers)
