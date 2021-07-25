import codecs
import re
from xml.sax.saxutils import escape

import arrow
from kodi_six import xbmcplugin
from six.moves.urllib_parse import urlparse, parse_qsl

from slyguy import plugin, gui, settings, userdata, signals, inputstream
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_TAG

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

    folder.add_item(label=_(_.HOME, _bold=True), path=plugin.url_for(content, slug='home'))
    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    folder.add_item(label=_(_.OLYMPICS, _bold=True), path=plugin.url_for(content, slug='olympics'))
    folder.add_item(label=_(_.SHOWS, _bold=True), path=plugin.url_for(shows))
    folder.add_item(label=_(_.MOVIES, _bold=True), path=plugin.url_for(content, slug='movies'))
    folder.add_item(label=_(_.SPORT, _bold=True), path=plugin.url_for(content, slug='sport'))
    folder.add_item(label=_(_.NEWS, _bold=True), path=plugin.url_for(content, slug='news'))
    folder.add_item(label=_(_.CATEGORIES, _bold=True), path=plugin.url_for(content, slug='all-categories'))
    folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(search))

    if settings.getBool('bookmarks', True):
        folder.add_item(label=_(_.BOOKMARKS, _bold=True),  path=plugin.url_for(plugin.ROUTE_BOOKMARKS), bookmark=False)

    folder.add_item(label=_.SETTINGS, path=plugin.url_for(plugin.ROUTE_SETTINGS), _kiosk=False, bookmark=False)

    return folder

def _get_url(url):
    url = url.rstrip('/').split('/')[-1]

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query))
    if not params or 'channel-id' not in params:
        return url

    return params['channel-id']

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    return _process_rows(api.search(query)), False

def _process_rows(rows, slug='', expand_media=False, season_name=''):
    items = []
    now = arrow.now()

    for row in rows:
        item = None
        if row['type'] in ('mediaShelf', 'channelShelf') and row['cName'] not in ('My Watchlist', 'Continue Watching'):
            if expand_media:
                items.extend(_process_rows(row.get('mediaItems', []), slug=slug))
            else:
                item = plugin.Item(
                    label = row['title'],
                    info = {'plot': row.get('description')},
                    path = plugin.url_for(component, slug=slug, id=row['id'], label=row['title']),
                )

        if row['type'] == 'EpisodeContainer':
            title = re.sub('^([0-9]+\.)', '', row['cardData']['title'])

            info = {
                'plot': row['cardData'].get('synopsis') or row.get('infoPanelData', {}).get('shortSynopsis') or row['cardData'].get('subtitle'),
                'mediatype': 'episode',
            }

            if 'infoPanelData' in row:
                info['tvshowtitle'] = row['infoPanelData']['seriesLogo']['name']

            def _get_duration(row):
                patterns = ['([0-9]+)h ([0-9]+)m', '([0-9]+)m']

                strings = [row['cardData']['subtitle']]
                if 'infoPanelData' in row:
                    strings.insert(0, row['infoPanelData']['subtitle'])

                for string in strings:
                    for pattern in patterns:
                        match = re.search(pattern, string)
                        if match:
                            if len(match.groups()) == 2:
                                return (int(match.group(1))*60 + int(match.group(2)))*60
                            elif len(match.groups()) == 1:
                                return int(match.group(1))*60

                return 0

            def _get_season_episode(row):
                titles = [row['cardData']['title'], row['cardData']['image'].get('altTag','')]
                if 'infoPanelData' in row:
                    titles.insert(0, row['infoPanelData']['title'])

                patterns = ['(S([0-9]+) E([0-9]+))', '(Season ([0-9]+)) Episode ([0-9]+)', '(Year ([0-9]+)) Episode ([0-9]+)']

                for title in titles:
                    title = re.sub('^([0-9]+\.)', '', title)

                    for pattern in patterns:
                        match = re.search(pattern, title)
                        if match:
                            return int(match.group(2)), int(match.group(3))

                return None, None

            info['season'], info['episode'] = _get_season_episode(row)
            info['duration'] = _get_duration(row)

            item = plugin.Item(
                label = title,
                info = info,
                art  = {'thumb': IMAGE_URL.format(url=row['cardData']['image']['url'], width=IMAGE_WIDTH)},
                playable = True,
            )

            if 'playerData' in row:
                parsed = urlparse(row['playerData']['videoUrl'])
                params = dict(parse_qsl(parsed.query))
                item.path = plugin.url_for(play, account=params['accountId'], reference=params['referenceId'])
            else:
                item.path = plugin.url_for(play_vod, slug=_get_url(row['cardData']['contentLink']['url']))

        if row['type'] == 'carousel':
            item = plugin.Item(
                label = _.FEATURED,
                info = {'plot': row.get('description')},
                path = plugin.url_for(component, slug=slug, id=row['id'], label=_.FEATURED),
            )

        if row['type'] in ('SeriesCard', 'contentLinkedImage'):
            item = plugin.Item(
                label = row.get('title') or row['image']['altTag'] or row.get('cName'),
                info = {'plot': row.get('lozengeText')},
                art = {'thumb': IMAGE_URL.format(url=row['image']['url'], width=IMAGE_WIDTH)},
            )

            if '/live/' in row['contentLink']['url'] or LIVE_TV_SLUG in row['contentLink']['url']:
                item.path = plugin.url_for(play_channel, slug=_get_url(row['contentLink']['url']), _is_live=True)
                item.playable = True
                if 'channelLogo' in row:
                    item.art['fanart'] = IMAGE_URL.format(url=row['channelLogo']['url'], width=1000)
            else:
                item.path = plugin.url_for(content, slug=_get_url(row['contentLink']['url']))

        if row['type'] == 'ChannelItem':
            plot = u''
            count = 0
            image = IMAGE_URL.format(url=row['channelLogo']['url'], width=IMAGE_WIDTH)
            fanart = None

            for epg in row['schedules']['items']:
                start = arrow.get(epg['startTime'])
                stop  = arrow.get(epg['endTime'])

                if (now > start and now < stop) or start > now:
                    if count == 0:
                        fanart = IMAGE_URL.format(url=epg['mediaImage']['url'], width=1000)
                    plot += u'[{}] {}\n'.format(start.to('local').format('h:mma'), epg['title'])
                    count += 1

            item = plugin.Item(
                label = row['name'],
                info = {'plot': plot},
                art = {'thumb': image, 'fanart': fanart},
                path = plugin.url_for(play_channel, slug=_get_url(row['contentLink']['url']), _is_live=True),
                playable = True,
            )

        if item:
            items.append(item)

    return items

@plugin.route()
def shows(**kwargs):
    folder = plugin.Folder(_.SHOWS)

    data = api.content(SHOWS_SLUG)
    folder.add_item(label=_(_.ALL, _bold=True), path=plugin.url_for(component, slug=SHOWS_SLUG, id=data['id'], label=_.ALL, expand_media=1))

    items = _process_rows(data['items'], SHOWS_SLUG, False)
    folder.add_items(items)

    return folder

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(_.LIVE_TV)

    rows = _get_live_channels()
    items = _process_rows(rows, LIVE_TV_SLUG)
    folder.add_items(items)

    return folder

@plugin.route()
def content(slug, label=None, expand_media=0, **kwargs):
    data = api.content(slug)

    if data['pageMetaData']['pageEventName'] == 'vodPage':
        return show(slug, data)

    folder = plugin.Folder(label or data['title'])
    items = _process_rows(data['items'], slug, int(expand_media))
    folder.add_items(items)

    return folder

def show(slug, data):
    show_name = data['pageMetaData']['pageTitle']
    plot = data['pageMetaData']['description']
    thumb = IMAGE_URL.format(url=data['items'][0]['thumbnail']['url'], width=IMAGE_WIDTH)
    fanart = IMAGE_URL.format(url=data['items'][0]['primaryBackgroundImage']['url'], width=1000)

    folder = plugin.Folder(data['title'], fanart=fanart)

    seasons = []
    similiar = None
    clips = None

    for section in data['items']:
        for row in section.get('items') or []:
            if row.get('cName') == 'Clips':
                clips = row['id']
                continue

            if row.get('cName') == 'More Like This':
                similiar = row['id']
                continue

            for row2 in row.get('items') or []:
                for row3 in row2.get('items') or []:
                    for row4 in row3.get('items') or []:
                        if row4.get('childType') == 'EpisodeContainer':
                            try: season = int(row3['title'])
                            except: season = row3['title']

                            seasons.append([season, row2['title'], row4])

    seasons = sorted(seasons, key=lambda x: x[0])
    if len(seasons) == 1 and settings.getBool('flatten_single_season', True):
        items = _process_rows(seasons[0][2].get('mediaItems', []), '{} {}'.format(seasons[0][1], seasons[0][0]))
        folder.sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED]
        folder.add_items(items)
    else:
        for season in seasons:
            folder.add_item(
                label = '{} {}'.format(season[1], season[0]),
                art = {'thumb': thumb, 'fanart': fanart},
                info = {'plot': plot},
                path = plugin.url_for(component, slug=slug, id=season[2]['id'], label=show_name, episodes=1, fanart=fanart),
            )

    if clips and not settings.getBool('hide_clips', False):
        folder.add_item(
            label = 'Clips',
            art = {'thumb': thumb, 'fanart': fanart},
            info = {'plot': plot},
            path = plugin.url_for(component, slug=slug, id=clips, label=show_name, fanart=fanart, expand_media=1),
            specialsort = 'bottom',
        )

    if similiar and not settings.getBool('hide_suggested', False):
        folder.add_item(
            label = _.SUGGESTED,
            art = {'thumb': thumb, 'fanart': fanart},
            info = {'plot': plot},
            path = plugin.url_for(component, slug=slug, id=similiar, label=show_name, fanart=fanart, expand_media=1),
            specialsort = 'bottom',
        )

    return folder

@plugin.route()
def component(slug, id, label, expand_media=0, episodes=0, fanart=None, **kwargs):
    expand_media = int(expand_media)
    episodes = int(episodes)

    folder = plugin.Folder(label, fanart=fanart)
    if episodes:
        folder.sort_methods = [xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL, xbmcplugin.SORT_METHOD_DATEADDED]

    items = _process_rows(api.component(slug, id)['items'], slug, expand_media)
    folder.add_items(items)

    return folder

@plugin.route()
def play_vod(slug, **kwargs):
    data = api.content(slug)

    url = None
    for row in data.get('items', []):
        for row2 in row.get('items', []):
            if row2.get('videoUrl'):
                url = row2['videoUrl']
                break

    if not url:
        raise PluginError(_.NO_VIDEO)

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query))

    return _play(params['accountId'], params['referenceId'], live=False)

@plugin.route()
def play_channel(slug, **kwargs):
    data = api.video_player(slug)
    url = data['videoUrl']

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query))

    item = _play(params['accountId'], params['referenceId'], live=True)
    item.label = data['posterImage']['altTag']
    item.art = {'thumb': IMAGE_URL.format(url=data['posterImage']['url'], width=IMAGE_WIDTH)}

    return item

@plugin.route()
def play(account, reference, **kwargs):
    return _play(account, reference, live=ROUTE_LIVE_TAG in kwargs)

def _play(account, reference, live=False):
    item = api.play(account, reference, live)

    if live and item.inputstream:
        item.inputstream.live = True
        item.inputstream.force = True

    return item

def _get_live_channels():
    data = api.content(LIVE_TV_SLUG)

    for section in data['items']:
        if section['type'] == 'channelShelf' and section['cName'] == 'Live':
            return section.get('mediaItems', [])

    return []

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U')

        for channel in _get_live_channels():
            f.write(u'\n#EXTINF:-1 tvg-chno="{chno}" tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                chno=channel['channelId'], id=channel['channelId'], name=channel['name'], logo=IMAGE_URL.format(url=channel['channelLogo']['url'], width=IMAGE_WIDTH),
                    url=plugin.url_for(play_channel, slug=_get_url(channel['contentLink']['url']), _is_live=True),
            ))

@plugin.route()
@plugin.merge()
def epg(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'<?xml version="1.0" encoding="utf-8" ?><tv>')

        for channel in _get_live_channels():
            f.write(u'<channel id="{id}"></channel>'.format(id=channel['channelId']))
            for epg in channel['schedules']['items']:
                start = arrow.get(epg['startTime'])
                stop  = arrow.get(epg['endTime'])

                icon = u'<icon src="{}"/>'.format(escape(IMAGE_URL.format(url=epg['mediaImage']['url'], width=IMAGE_WIDTH))) if epg['mediaImage'].get('url') else ''
                desc = u'<desc>{}</desc>'.format(escape(epg['synopsis'])) if epg['synopsis'] else ''
                genre = u'<category lang="en">{}</category>'.format(escape(epg['genre'])) if epg['genre'] else ''

                subtitle = u'<subtitle>{}</subtitle>'.format(escape(epg['subTitle']).strip()) if epg['subTitle'] else ''
                if not subtitle:
                    subtitle = u'<subtitle>{}</subtitle>'.format(escape(epg['subTitle2']).strip()) if epg['subTitle2'] else ''

                f.write(u'<programme channel="{id}" start="{start}" stop="{stop}"><title>{title}</title>{subtitle}{desc}{icon}{genre}</programme>'.format(
                    id=channel['channelId'], start=start.format('YYYYMMDDHHmmss Z'), stop=stop.format('YYYYMMDDHHmmss Z'), title=escape(epg['title']),
                    subtitle=subtitle, desc=desc, icon=icon, genre=genre,
                ))

        f.write(u'</tv>')

@plugin.route()
def login(**kwargs):
    username = gui.input(_.ASK_USERNAME, default=userdata.get('username', '')).strip()
    if not username:
        return

    userdata.set('username', username)

    password = gui.input(_.ASK_PASSWORD, hide_input=True).strip()
    if not password:
        return

    api.login(username, password)
    gui.refresh()


@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(_.LOGOUT_YES_NO):
        return

    api.logout()
    gui.refresh()
