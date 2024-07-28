import re
import codecs
from xml.sax.saxutils import escape

import arrow
from six.moves.urllib_parse import urlparse, parse_qsl, quote_plus

from slyguy import plugin, signals, mem_cache
from slyguy.exceptions import PluginError
from slyguy.constants import ROUTE_LIVE_TAG

from .api import API
from .language import _
from .settings import settings
from .constants import *

api = API()

@signals.on(signals.BEFORE_DISPATCH)
def before_dispatch():
    api.new_session()
    plugin.logged_in = api.logged_in

@plugin.route('')
def home(**kwargs):
    folder = plugin.Folder(cacheToDisc=False)

    folder.add_item(label=_(_.LIVE_TV, _bold=True), path=plugin.url_for(live_tv))
    folder.add_item(label=_(_.FEATURED, _bold=True), path=plugin.url_for(content, slug='ctv-home'))
    _nav(folder)
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

@mem_cache.cached(60*5)
def _nav(folder):
    skips = ['live-tv']

    replaces = {
        'shows': plugin.url_for(shows),
    }

    for row in api.nav():
        slug = row['contentLink'].lstrip('/')
        if slug in skips:
            continue
        path = replaces.get(slug, plugin.url_for(content, slug=slug))
        folder.add_item(
            label = _(row['title'], _bold=True),
            path = path,
        )

@plugin.route()
@plugin.search()
def search(query, page, **kwargs):
    return _process_rows(api.search(query)), False

def _image(url, width=IMAGE_WIDTH):
    return IMAGE_URL.format(url=quote_plus(url.encode('utf8')), width=width)

def _process_rows(rows, slug='', expand_media=False, season_num=0):
    items = []
    now = arrow.now()

    count = len(rows)
    for row in rows:
        if not row:
            # probably api version needs bumping
            continue

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
            }

            if 'infoPanelData' in row:
                info['tvshowtitle'] = row['infoPanelData']['seriesLogo']['name']

            def _get_duration(row):
                patterns = [
                    ['([0-9]+)h ([0-9]+)m ([0-9]+)s', lambda match: int(match.group(1))*3600 + int(match.group(2))*60 + int(match.group(3))],
                    ['([0-9]+)h ([0-9]+)m', lambda match: int(match.group(1))*3600 + int(match.group(2))*60],
                    ['([0-9]+)m$', lambda match: int(match.group(1))*60],
                    ['([0-9]+)s$', lambda match: int(match.group(1))],
                ]

                strings = [row['cardData'].get('duration','')]
                if 'infoPanelData' in row:
                    strings.insert(0, row['infoPanelData']['subtitle'])

                for string in strings:
                    for pattern in patterns:
                        match = re.search(pattern[0], string)
                        if match:
                            return pattern[1](match)

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

            if not info['season'] and not info['episode'] and count == 1:
                info['mediatype'] = 'movie'
                info['year'] = season_num
            else:
                info['mediatype'] = 'episode'

            item = plugin.Item(
                label = title,
                info = info,
                art  = {'thumb': _image(row['cardData']['image']['url'])},
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
            art = {'thumb': _image(row['image']['url'])}
            if 'seriesBackgroundImage' in row:
                art['fanart'] = _image(row['seriesBackgroundImage']['url'], width=1000)

            item = plugin.Item(
                label = row.get('title') or row['image']['altTag'] or row.get('cName'),
                info = {
                    'plot': row.get('description'),
                    'mediatype': 'tvshow',
                },
                art = art,
            )

            if '/live/' in row['contentLink']['url'] or LIVE_TV_SLUG in row['contentLink']['url']:
                item.path = plugin.url_for(play_channel, slug=_get_url(row['contentLink']['url']), _is_live=True)
                item.playable = True
                if 'channelLogo' in row:
                    item.art['fanart'] = _image(row['channelLogo']['url'], width=1000)
            else:
                item.path = plugin.url_for(content, slug=_get_url(row['contentLink']['url']), thumb=row['image']['url'])

        if row['type'] == 'ChannelItem':
            plot = u''
            count = 0
            image = _image(row['channelLogo']['url'])
            fanart = None

            for epg in row['schedules']['items']:
                start = arrow.get(epg['startTime'])
                stop  = arrow.get(epg['endTime'])

                if (now > start and now < stop) or start > now:
                    if count == 0:
                        fanart = _image(epg['mediaImage']['url'], width=1000)
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

    items = _process_rows(data['items'], SHOWS_SLUG)
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
def content(slug, label=None, thumb=None, expand_media=0, **kwargs):
    data = api.content(slug)

    if data['pageMetaData']['pageEventName'] == 'vodPage':
        return show(slug, data, thumb)

    folder = plugin.Folder(label or data['title'])
    items = _process_rows(data['items'], slug, int(expand_media))
    folder.add_items(items)

    return folder

def show(slug, data, thumb=None):
    show_name = data['pageMetaData']['pageTitle']
    plot = data['pageMetaData']['description']
    thumb = _image(thumb or data['pageMetaData']['objectGraphImage']['url'])
    fanart = _image(data['items'][0]['backgroundImage']['url'], width=1000)

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
                            try: season_num = int(row3['title'])
                            except: season_num = None

                            if season_num:
                                label = _(_.SEASON, number=season_num)
                                sort = season_num
                            else:
                                label = row3['title']
                                sort = 0

                            seasons.append([sort, label, row4])

    seasons = sorted(seasons, key=lambda x: x[0])
    if len(seasons) == 1 and (settings.getBool('flatten_single_season', True) or len(seasons[0][2].get('mediaItems', [])) <= 1):
        items = _process_rows(seasons[0][2].get('mediaItems', []), season_num=seasons[0][0])
        folder.add_items(items)
    else:
        for season in seasons:
            folder.add_item(
                label = season[1],
                art = {'thumb': thumb, 'fanart': fanart},
                info = {
                    'plot': plot,
                    'mediatype': 'season',
                    'tvshowtitle': data['title'],
                },
                path = plugin.url_for(component, slug=slug, id=season[2]['id'], label=show_name, fanart=fanart),
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
def component(slug, id, label, expand_media=0, fanart=None, **kwargs):
    expand_media = int(expand_media)

    folder = plugin.Folder(label, fanart=fanart)
    items = _process_rows(api.component(slug, id)['items'], slug, expand_media)
    folder.add_items(items)

    return folder

@plugin.route()
def play_vod(slug, **kwargs):
    data = api.content(slug)

    url = None
    for row in data.get('items') or []:
        for row2 in row.get('items') or []:
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
    item.art = {'thumb': _image(data['posterImage']['url'])}

    return item

@plugin.route()
def play(account, reference, **kwargs):
    return _play(account, reference, live=ROUTE_LIVE_TAG in kwargs)

def _play(account, reference, live=False):
    item = api.play(account, reference, live)
    item.headers = HEADERS

    if live and item.inputstream:
        item.inputstream.live = True
        item.inputstream.force = True

    return item

def _get_live_channels():
    data = api.content(LIVE_TV_SLUG)

    added = []
    channels = []

    for section in data['items']:
        if section.get('childType') != 'channelItem':
            continue

        for row in section.get('mediaItems', []):
            if row.get('type') == 'ChannelItem' and row['channelId'] not in added:
                channels.append(row)
                added.append(row['channelId'])

    return sorted(channels, key=lambda x: int(x['channelId']))

@plugin.route()
@plugin.merge()
def playlist(output, **kwargs):
    with codecs.open(output, 'w', encoding='utf8') as f:
        f.write(u'#EXTM3U x-tvg-url="{}"'.format(plugin.url_for(epg, output='$FILE')))

        for channel in _get_live_channels():
            f.write(u'\n#EXTINF:-1 tvg-chno="{chno}" tvg-id="{id}" tvg-name="{name}" tvg-logo="{logo}",{name}\n{url}'.format(
                chno=channel['channelId'], id=channel['channelId'], name=channel['name'], logo=_image(channel['channelLogo']['url']),
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

                icon = u'<icon src="{}"/>'.format(escape(_image(epg['mediaImage']['url']))) if epg['mediaImage'].get('url') else ''
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
